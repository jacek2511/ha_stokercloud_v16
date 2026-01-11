import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD
from .coordinator import StokerCloudV16Coordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Konfiguracja integracji po dodaniu przez interfejs użytkownika."""
    
    # Pobieramy dane zapisane w Config Flow
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    # Tworzymy instancję koordynatora
    coordinator = StokerCloudV16Coordinator(hass, username, password)

    # Pierwsze odświeżenie przy starcie, aby sensory od razu miały dane
    await coordinator.async_config_entry_first_refresh()

    # Zapisujemy koordynatora w pamięci podręcznej HA
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Rejestrujemy platformy (sensory, suwaki temperatury)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "number"])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Obsługa usuwania integracji."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "number"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
