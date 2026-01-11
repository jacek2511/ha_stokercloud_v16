import logging
from datetime import timedelta

import async_timeout
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from stokercloud_v16.client import StokerCloudClientV16  # Nazwa Twojej nowej biblioteki
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class StokerCloudV16Coordinator(DataUpdateCoordinator):
    """Scentralizowany koordynator pobierania danych z API v16."""

    def __init__(self, hass, username, password):
        """Inicjalizacja koordynatora."""
        self.client = StokerCloudClientV16(
            username, 
            password, 
            session=async_get_clientsession(hass)
        )
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"StokerCloud V16 ({username})",
            update_interval=timedelta(minutes=1),
        )

    async def _async_update_data(self):
        """Pobierz dane przez bibliotekę kliencką."""
        try:
            # Ustawiamy timeout na 15 sekund, aby wolne API nie zawiesiło HA
            async with async_timeout.timeout(15):
                data = await self.client.fetch_data()
                if not data:
                    raise UpdateFailed("API zwróciło pusty wynik")
                return data
        except Exception as err:
            raise UpdateFailed(f"Błąd komunikacji z API StokerCloud: {err}")
