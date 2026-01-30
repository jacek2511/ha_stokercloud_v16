import logging
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.restore_state import RestoreEntity
from .entity import StokerEntity
from .const import DOMAIN, SIMPLE_NUMBERS_CONFIG

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Konfiguracja parametrów numerycznych NBE StokerCloud."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    username = coordinator.client.username.lower()

    # 1. Generowanie standardowych suwaków z konfiguracji
    entities = [StokerGenericNumber(coordinator, username, *cfg) for cfg in SIMPLE_NUMBERS_CONFIG]
    
    async_add_entities(entities)

class StokerBaseNumber(StokerEntity, NumberEntity, RestoreEntity):
    """Wspólna logika dla suwaków integracji StokerCloud."""
    
    def __init__(self, coordinator, username):
        super().__init__(coordinator, username)
        self._attr_mode = NumberMode.BOX

    async def async_added_to_hass(self):
        """Przywracanie poprzedniej wartości po restarcie HA."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) and \
           last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._attr_native_value = float(last_state.state)
            except ValueError:
                _LOGGER.warning("Nie udało się przywrócić wartości dla %s", self.entity_id)

    async def async_set_native_value(self, value: float) -> None:
        """Zapisuje nową wartość i odświeża obliczenia."""
        self._attr_native_value = value
        self.async_write_ha_state()


class StokerGenericNumber(StokerBaseNumber):
    """Uniwersalna klasa dla suwaków pomocniczych (ceny, pojemności, progi)."""
    
    def __init__(self, coordinator, username, sid, name, v_min, v_max, step, unit, icon, default, mode):
        super().__init__(coordinator, username)
        self.entity_id = f"number.nbe_{sid}"
        self._attr_name = name
        self._attr_unique_id = f"nbe_{username}_{sid}"
        self._attr_native_min_value = v_min
        self._attr_native_max_value = v_max
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_native_value = default
        self._attr_mode = mode