class StokerSensor(SensorEntity):
    def __init__(self, coordinator, name, key, unit, device_class):
        self.coordinator = coordinator
        self._name = name
        self._key = key
        self._unit = unit
        self._device_class = device_class

    @property
    def name(self):
        return f"Stoker {self._name}"

    @property
    def native_value(self):
        # Główny stan sensora
        return self.coordinator.data.get(self._key)

    @property
    def extra_state_attributes(self):
        """Mapuje wszystkie parametry API jako atrybuty sensora."""
        # Pobieramy przygotowany wcześniej słownik wszystkich danych
        attrs = self.coordinator.data.get("all_attributes", {})
        
        # Możemy dodać też specyficzne informacje dla tego konkretnego sensora
        # np. jeśli to sensor temperatury, dodajmy info o modelu i wersji
        if self._key == "boiler_temp":
            return attrs
        
        # Dla pozostałych sensorów możemy zwracać tylko podstawowe atrybuty 
        # lub również całość, jeśli chcemy mieć dostęp do nich wszędzie.
        return attrs

    @property
    def native_unit_of_measurement(self):
        return self._unit

    @property
    def device_class(self):
        return self._device_class
