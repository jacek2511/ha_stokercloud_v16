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
        try:
            async with async_timeout.timeout(50): # Całkowity czas na wszystkie zapytania
                
                try:
                    data = await self.client.fetch_data()
                except Exception as e:
                    raise UpdateFailed(f"Błąd fetch_data: {e}")

                if not data or not isinstance(data, dict):
                    raise UpdateFailed("API zwróciło pusty obiekt lub błędny format danych")

                now = datetime.now()

                stat_results = {"current_hour": 0.0, "previous_hour": 0.0, "day": 0.0, "yesterday": 0.0, "dhw_day": 0.0, "month": 0.0, "year": 0.0}
                
                try:
                    h_task = self.client.get_consumption("hours=24")
                    d_task = self.client.get_consumption("days=2")
                    m_task = self.client.get_consumption("months=12")
                    y_task = self.client.get_consumption("years=12")
                    
                    hourly_stats, daily_stats, monthly_stats, yearly_stats = await asyncio.gather(
                        h_task, d_task, m_task, y_task, return_exceptions=True
                    )

                    def get_safe(lst, s_idx, d_idx):
                        if not isinstance(lst, list) or len(lst) <= s_idx:
                            return 0.0
                        sub = lst[s_idx]
                        if not isinstance(sub, dict) or "data" not in sub:
                            return 0.0
                        data_points = sub["data"]
                        if not isinstance(data_points, list) or len(data_points) <= d_idx:
                            return 0.0
                        try:
                            val = data_points[d_idx][1]
                            return float(str(val).replace(",", "."))
                        except (ValueError, TypeError, IndexError):
                            return 0.0
                    
                    if all(isinstance(x, list) for x in [hourly_stats, daily_stats, monthly_stats, yearly_stats]):
                        stat_results.update({
                            "current_hour": get_safe(hourly_stats, 0, 0),
                            "previous_hour": get_safe(hourly_stats, 0, 1),
                            "day": get_safe(daily_stats, 0, 0),
                            "yesterday": get_safe(daily_stats, 0, 1),
                            "dhw_day": get_safe(daily_stats, 1, 0),
                            "month": get_safe(monthly_stats, 0, 0),
                            "year": get_safe(yearly_stats, 0, 0)
                        })
                    
                    data["stats"] = stat_results

                except Exception as stats_err:
                    _LOGGER.warning("Problem ze statystykami: %s. Używam poprzednich danych.", stats_err)
                    # Próba odzyskania statystyk z poprzedniego cyklu
                    if self.data and "stats" in self.data:
                        data["stats"] = self.data["stats"]
                    else:
                        data["stats"] = stat_results

                # 3. OBSŁUGA MENU / KONFIGURACJI
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

                # Zawsze wstrzykuj dane menu (z cache lub nowe)
                data["menus_flat"] = self._cached_menus.get("flat", {})
                if not data.get("menus"):
                    data["menus"] = self._cached_menus.get("raw", {})

                return data

        except asyncio.TimeoutError:
            raise UpdateFailed("Przekroczono czas oczekiwania na odpowiedź ze StokerCloud")
        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.error("Błąd krytyczny koordynatora: %s", err)
            raise UpdateFailed(f"Błąd komunikacji: {err}")