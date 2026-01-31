"""Klasa bazowa dla encji NBE."""
from __future__ import annotations
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

class StokerEntity(CoordinatorEntity):
    """Wspólna klasa bazowa definiująca urządzenie NBE."""

    def __init__(self, coordinator, username: str) -> None:
        super().__init__(coordinator)
        self._username = username.lower()
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._username)},
            name=f"Kocioł NBE ({self._username})",
            manufacturer="NBE",
            model="StokerCloud Controller",
            configuration_url="https://www.stokercloud.dk",
        )

    def _get_api_data(self, path: str, default=None):
        """Metoda pomocnicza dostępna dla wszystkich typów encji."""
        val = self.coordinator.data
        if not val: return default
        for part in path.split("."):
            if not isinstance(val, dict): return default
            val = val.get(part)
        return val if val is not None else default

    def _get_value_safely(self, entity_id, default=0.0):
        state = self.hass.states.get(entity_id)
        if state and state.state not in ["unknown", "unavailable", None]:
            try: return float(state.state)
            except ValueError: return default
        return default
