from homeassistant.components.number import NumberEntity
from homeassistant.const import UnitOfTemperature
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        StokerTemperatureNumber(coordinator, "Zadana Kotła", "-wantedboilertemp", 40, 85),
        StokerTemperatureNumber(coordinator, "Zadana CWU", "dhwwanted", 10, 65),
    ]
    async_add_entities(entities)

class StokerTemperatureNumber(NumberEntity):
    def __init__(self, coordinator, name, key, min_val, max_val):
        self.coordinator = coordinator
        self._name = name
        self._key = key
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = 1.0
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def name(self):
        return f"Stoker {self._name}"

    @property
    def unique_id(self):
        return f"{self.coordinator.client.username}_set_{self._key}"

    @property
    def native_value(self):
        """Pobiera aktualnie ustawioną wartość z atrybutów front_data."""
        front_data = self.coordinator.data.get("all_attributes", {}).get("front_data", {})
        val = front_data.get(self._key)
        try:
            return float(val) if val else None
        except ValueError:
            return None

    async def async_set_native_value(self, value: float):
        """Wysyła nową wartość do API."""
        success = await self.coordinator.client.set_param(self._key, value)
        if success:
            # Wymuszamy odświeżenie danych, aby suwak nie odskoczył
            await self.coordinator.async_request_refresh()
