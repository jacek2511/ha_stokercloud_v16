import logging
from datetime import timedelta, datetime
import async_timeout
import asyncio
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

class StokerCloudV16Coordinator(DataUpdateCoordinator):
    """Koordynator z inteligentnym cache i zabezpieczeniami NoneType."""

    def __init__(self, hass, client):
        self.client = client
        self.username = client.username.lower()
        
        # Cache dla danych rzadko zmienianych (Konfiguracja)
        self._cached_menus = {"flat": {}, "raw": {}}
        self._last_menu_update = None
        
        super().__init__(
            hass,
            _LOGGER,
            name="StokerCloud v16",
            update_interval=timedelta(seconds=60), 
        )

    def _flatten_menu(self, menu_name: str, menu_data: dict | list | None) -> dict:
        """Spłaszcz menu do słownika z zabezpieczeniem przed błędami struktury."""
        flat = {}
        if not menu_data: return flat
        
        try:
            if isinstance(menu_data, dict):
                items = menu_data.items()
            elif isinstance(menu_data, list):
                items = [(str(i.get("id")), i.get("value")) for i in menu_data if isinstance(i, dict)]
            else:
                return flat

            for k, v in items:
                val = None if v == "N/A" else v
                flat[f"menus_{menu_name}_{k}"] = val
        except Exception as e:
            _LOGGER.debug("Błąd spłaszczania menu %s: %s", menu_name, e)
        return flat

    async def _async_update_data(self):
        """Pobierz dane z API z inteligentnym mechanizmem retry i cache."""
        max_retries = 2
        retry_delay = 5
        
        for attempt in range(max_retries + 1):
            try:
                # 1. POBIERANIE DANYCH GŁÓWNYCH Z LIMITAMI CZASOWYMI
                async with async_timeout.timeout(30):
                    data = await self.client.fetch_data()
                
                if not data or not isinstance(data, dict):
                    raise ValueError("Pusty lub błędny format danych z API")

                now = datetime.now()

                # 2. AKTUALIZACJA STATYSTYK SPALANIA
                stat_results = {
                    "current_hour": 0.0, "previous_hour": 0.0, "day": 0.0, 
                    "yesterday": 0.0, "dhw_day": 0.0, "month": 0.0, "year": 0.0
                }
                
                try:
                    # Równoległe pobieranie
                    tasks = [
                        self.client.get_consumption("hours=24"),
                        self.client.get_consumption("days=2"),
                        self.client.get_consumption("months=12"),
                        self.client.get_consumption("years=12")
                    ]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Rozpakowanie wyników (sprawdzenie czy nie są wyjątkami)
                    h_stats = results[0] if isinstance(results[0], list) else []
                    d_stats = results[1] if isinstance(results[1], list) else []
                    m_stats = results[2] if isinstance(results[2], list) else []
                    y_stats = results[3] if isinstance(results[3], list) else []

                    def get_safe(lst, s_idx, d_idx):
                        """Bezpieczne wyciąganie wartości z głębokiej struktury JSON."""
                        try:
                            if not isinstance(lst, list) or len(lst) <= s_idx:
                                return 0.0
                            sub = lst[s_idx]
                            if not isinstance(sub, dict) or "data" not in sub:
                                return 0.0
                            data_points = sub["data"]
                            if not isinstance(data_points, list) or len(data_points) <= d_idx:
                                return 0.0
                            val = data_points[d_idx][1]
                            return float(str(val).replace(",", "."))
                        except (ValueError, TypeError, IndexError):
                            return 0.0

                    stat_results.update({
                        "current_hour": get_safe(h_stats, 0, 0),
                        "previous_hour": get_safe(h_stats, 0, 1),
                        "day": get_safe(d_stats, 0, 0),
                        "yesterday": get_safe(d_stats, 0, 1),
                        "dhw_day": get_safe(d_stats, 1, 0),
                        "month": get_safe(m_stats, 0, 0),
                        "year": get_safe(y_stats, 0, 0)
                    })
                    data["stats"] = stat_results

                except Exception as stats_err:
                    _LOGGER.debug("Błąd statystyk (próba %s): %s", attempt + 1, stats_err)
                    # Jeśli mamy stare statystyki, używamy ich zamiast zer
                    data["stats"] = self.data.get("stats", stat_results) if self.data else stat_results

                # 3. OBSŁUGA MENU / KONFIGURACJI (z Cache)
                should_update_menu = (
                    self._last_menu_update is None or 
                    now - self._last_menu_update > timedelta(hours=1)
                )

                if should_update_menu and "menus" in data:
                    menus_flat = {}
                    menus_raw = data.get("menus", {})
                    if isinstance(menus_raw, dict):
                        for menu_name, menu_data in menus_raw.items():
                            menus_flat.update(self._flatten_menu(menu_name, menu_data))
                        
                        self._cached_menus["flat"] = menus_flat
                        self._cached_menus["raw"] = menus_raw
                        self._last_menu_update = now

                # Zawsze wstrzykuj dane menu (z cache lub świeżo pobrane)
                data["menus_flat"] = self._cached_menus.get("flat", {})
                if not data.get("menus"):
                    data["menus"] = self._cached_menus.get("raw", {})

                # Jeśli dotarliśmy tutaj, sukces! Zwracamy dane.
                return data

            except (asyncio.TimeoutError, ValueError, Exception) as err:
                if attempt < max_retries:
                    _LOGGER.debug("Błąd w próbie %s: %s. Ponawiam za %s sek...", attempt + 1, err, retry_delay)
                    await asyncio.sleep(retry_delay)
                else:
                    # Ostateczna próba nieudana
                    if isinstance(err, asyncio.TimeoutError):
                        raise UpdateFailed("Przekroczono czas oczekiwania na StokerCloud (Timeout)")
                    _LOGGER.error("Błąd krytyczny po %s próbach: %s", max_retries + 1, err)
                    raise UpdateFailed(f"Błąd komunikacji: {err}")
