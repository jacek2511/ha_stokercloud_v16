import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.restore_state import RestoreEntity
from .const import DOMAIN
from .entity import StokerEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Konfiguracja przełączników logicznych NBE StokerCloud."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    u = coordinator.client.username.lower()

    # Możesz przenieść tę listę do const.py jako SWITCHES_CONFIG, jeśli planujesz ich więcej
    SWITCHES_CONFIG = [
        ("extra_building_logic", "Uwzględniaj biuro w spalaniu", "mdi:office-building-cog", True),
    ]

    async_add_entities([
        StokerLogicSwitch(coordinator, u, *cfg) for cfg in SWITCHES_CONFIG
    ])

class StokerLogicSwitch(StokerEntity, SwitchEntity, RestoreEntity):
    """Przełącznik pomocniczy do sterowania logiką obliczeń wewnątrz HA."""
    
    def __init__(self, coordinator, username, sid, name, icon, default_state):
        super().__init__(coordinator, username)
        self.entity_id = f"switch.nbe_{sid}"
        self._attr_name = name
        self._attr_unique_id = f"nbe_{username}_{sid}"
        self._attr_icon = icon
        self._attr_is_on = default_state

    async def async_added_to_hass(self):
        """Przywracanie stanu po restarcie."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_is_on = (last_state.state == "on")

    @property
    def is_on(self) -> bool:
        """Zwraca aktualny stan przełącznika."""
        return self._attr_is_on

    async def async_turn_on(self, **kwargs):
        """Włącz logiczny parametr."""
        self._attr_is_on = True
        self.async_write_ha_state()
        # Opcjonalnie: wymuś odświeżenie sensorów zależnych
        # await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Wyłącz logiczny parametr."""
        self._attr_is_on = False
        self.async_write_ha_state()
        # Opcjonalnie: wymuś odświeżenie sensorów zależnych
        # await self.coordinator.async_request_refresh()