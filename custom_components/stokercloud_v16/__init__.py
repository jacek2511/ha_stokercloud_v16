import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession # DODAJ TO

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD
from .coordinator import StokerCloudV16Coordinator
from stokercloud_v16.client import StokerCloudClientV16 # Upewnij się, że ten import działa

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Konfiguracja integracji po dodaniu przez interfejs użytkownika."""
    
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    # 1. Tworzymy sesję aiohttp (standard w HA)
    session = async_get_clientsession(hass)

    # 2. Tworzymy klienta API
    client = StokerCloudClientV16(username, password, session)

    # 3. Tworzymy koordynatora i przekazujemy mu klienta
    # Zakładam, że Twój koordynator przyjmuje (hass, client) w __init__
    coordinator = StokerCloudV16Coordinator(hass, client)

    # 4. Pierwsze odświeżenie danych
    await coordinator.async_config_entry_first_refresh()

    # 5. Zapisujemy koordynatora
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # 6. Rejestrujemy platformy
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "binary_sensor", "number", "switch"])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Obsługa usuwania integracji."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "binary_sensor", "number", "switch"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
