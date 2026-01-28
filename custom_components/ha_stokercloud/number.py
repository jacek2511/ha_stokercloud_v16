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
    
    # 2. Specyficzne suwaki parametrów budynków
    entities.append(StokerInsulationNumber(coordinator, username, "Dom", "house", 0.60))
    entities.append(StokerInsulationNumber(coordinator, username, "Biuro", "extra", 1.00))

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
        
        # Opcjonalnie: Jeśli ten suwak wpływa na sensory obliczeniowe, 
        # wymuszamy przeliczenie danych w koordynatorze
        # await self.coordinator.async_request_refresh()

class StokerGenericNumber(StokerBaseNumber):
    
    def __init__(self, coordinator, username, sid, name, v_min, v_max, step, unit, icon, default):
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

class StokerInsulationNumber(StokerBaseNumber):
    """Suwak charakterystyki strat ciepła (kg/°C/24h)."""
    
    def __init__(self, coordinator, username, name, uid, default):
        super().__init__(coordinator, username)
        self.entity_id = f"number.nbe_insulation_factor_{uid}"
        self._attr_name = f"Charakterystyka strat - {name}"
        self._attr_unique_id = f"nbe_{username}_insulation_{uid}"
        self._attr_native_min_value = 0.05
        self._attr_native_max_value = 2.0
        self._attr_native_step = 0.01
        self._attr_native_unit_of_measurement = "kg/°C·d"
        self._attr_icon = "mdi:home-thermometer-outline"
        self._attr_native_value = default