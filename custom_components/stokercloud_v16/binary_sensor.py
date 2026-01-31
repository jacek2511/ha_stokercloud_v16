from __future__ import annotations
import logging
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.event import async_track_state_change_event

from .entity import StokerEntity
from .const import (
    DOMAIN, BINARY_SENSORS_CONFIG, OUTPUT_SENSORS_CONFIG, WEATHER_ZONE_TRANSLATIONS
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    u = coordinator.client.username.lower()

    entities = []
    entities.extend([StokerBinarySensor(coordinator, u, *cfg) for cfg in BINARY_SENSORS_CONFIG])
    entities.extend([StokerOutputBinarySensor(coordinator, u, *cfg) for cfg in OUTPUT_SENSORS_CONFIG])
    entities.extend([StokerWeatherZoneSensor(coordinator, u, i) for i in range(1, 5)])
    entities.append(StokerAnomalyBinarySensor(coordinator, u))

    async_add_entities(entities, update_before_add=True)


class StokerBaseBinary(StokerEntity, BinarySensorEntity): # Dziedziczymy po StokerEntity dla spójności device_info
    """Klasa bazowa dla sensorów binarnych."""
    def __init__(self, coordinator, username, uid, name):
        super().__init__(coordinator, username)
        self._uid = uid
        self._attr_name = name
        self._attr_unique_id = f"nbe_{username}_{uid}"
        # device_info jest już w StokerEntity, więc tutaj go nie powielamy

    def _resolve_path(self, path: str | list):
        """Ujednolicona metoda dostępu do danych (identyczna jak w sensor.py)."""
        val = self.coordinator.data
        parts = path.split(".") if isinstance(path, str) else path
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p)
            else:
                return None
        return val

class StokerBinarySensor(StokerBaseBinary):
    def __init__(self, coordinator, username, uid, name, path, device_class):
        super().__init__(coordinator, username, uid, name)
        self.entity_id = f"binary_sensor.nbe_{uid}"
        self._path = path
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool:
        val = self._resolve_path(self._path)
        if val is None: return False
        
        # Logika dla głównego stanu kotła (Working/Power vs Off/Alarm)
        if "state" in self._path:
            raw = str(val).lower()
            # Kocioł "pracuje" jeśli nie jest w stanie 0 (Off) ani 14 (Alarm)
            return not any(x in raw for x in ["state_0", "state_14", "lng_state_0", "lng_state_14"])
        
        # Dla innych wartości: 1, True, "ON" (case-insensitive)
        if isinstance(val, str):
            return val.upper() == "ON" or val == "1"
        return bool(val)

class StokerAnomalyBinarySensor(StokerBaseBinary):
    """Monitoruje drastyczne odchylenia od średniej wydajności."""
    def __init__(self, coordinator, username):
        super().__init__(coordinator, username, "efficiency_anomaly", "Anomalia wydajności domu")
        self.entity_id = "binary_sensor.nbe_efficiency_anomaly"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        try:
            # Używamy helperów, aby bezpiecznie pobrać stany encji
            s_now = self.hass.states.get("sensor.nbe_house_efficiency")
            s_mean = self.hass.states.get("sensor.nbe_mean_house_efficiency")
            s_thr = self.hass.states.get("number.nbe_anomaly_threshold")

            if not all([s_now, s_mean, s_thr]): return False
            
            val_now = float(s_now.state)
            val_mean = float(s_mean.state)
            threshold = float(s_thr.state) / 100
            
            # Jeśli aktualna wydajność jest o X% wyższa od średniej (co sugeruje błąd/wyciek ciepła)
            return val_now > (val_mean * (1 + threshold)) if val_mean > 0 else False
        except (ValueError, TypeError):
            return False

class StokerOutputBinarySensor(StokerBaseBinary):
    """Obsługuje wyjścia kotła (pompy, wentylatory, zawory)."""
    def __init__(self, coordinator, username, output_id, name, icon, slug):
        # uid budujemy z output_id, aby był unikalny
        super().__init__(coordinator, username, f"output_{output_id}", name)
        self.entity_id = f"binary_sensor.nbe_{slug}"
        self._output_id = output_id
        self._attr_icon = icon

    @property
    def is_on(self) -> bool:
        # Korzystamy z ujednoliconej ścieżki kropkowej
        val = self._resolve_path(f"leftoutput.{self._output_id}.val")
        return str(val).upper() == "ON"

    @property
    def extra_state_attributes(self):
        # Pobieramy cały obiekt wyjścia, aby mieć dostęp do 'name' i 'val'
        data = self._resolve_path(f"leftoutput.{self._output_id}")
        return data if isinstance(data, dict) else {}

class StokerWeatherZoneSensor(StokerBaseBinary):                                   
    """Sensor aktywno..ci strefy pogodowej."""                                
    def __init__(self, coordinator, username, zone):                   
        super().__init__(coordinator, username, f"weather_zone_{zone}", f"Strefa Pogodowa {zone}")
        self.entity_id = f"binary_sensor.nbe_weather_zone_{zone}"                                           
        self._zone = zone                                                                         
        self._attr_icon = "mdi:home-thermometer"                                                  
                                                                                                  
    @property                                                                                     
    def is_on(self) -> bool:                                     
        val = self._resolve_path(f"weathercomp.zone{self._zone}active")                               
        return str(val if val is not None else "0") == "1"                                                       
                                                                            
    @property                                                                           
    def extra_state_attributes(self):                                                               
        weather_comp = self._resolve_path("weathercomp")               
        if not isinstance(weather_comp, dict):                  
            return {}                                                                                               
                                                        
        prefix_dash = f"zone{self._zone}-"                    
        prefix_plain = f"zone{self._zone}"                           
                                                              
        return {                                                                       
            WEATHER_ZONE_TRANSLATIONS.get(k.replace(prefix_dash, "").replace(prefix_plain, ""), k): 
            (v.get("val") if isinstance(v, dict) else v)                                 
            for k, v in weather_comp.items() if k.startswith(prefix_plain)               
        }                                                                               
