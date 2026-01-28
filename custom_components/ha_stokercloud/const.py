from typing import Final
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.number import NumberDeviceClass, NumberMode
from homeassistant.const import (
    PERCENTAGE,
    UnitOfMass,
    UnitOfPower,
    UnitOfTemperature,
)

# --- KONFIGURACJA PODSTAWOWA ---
DOMAIN: Final = "ha_stokercloud_v16"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"

# --- ZEWNĘTRZNE ENCJE (ZALEŻNOŚCI) ---
ENTITY_WEATHER: Final = "sensor.nbe_weather_stokercloud"
ENTITY_BOILER_STATUS: Final = "sensor.nbe_boiler_status"
ENTITY_PUMP_OFFICE: Final = "binary_sensor.nbe_weather_pump_2"
ENTITY_PUMP_HOUSE: Final = "binary_sensor.nbe_weather_pump_1"
ENTITY_SWITCH_OFFICE: Final = "switch.nbe_extra_building_logic"
ENTITY_TEMP_TARGET_HOUSE: Final = "number.nbe_comfort_temperature"
ENTITY_TEMP_TARGET_OFFICE: Final = "number.nbe_extra_building_target_temp"
ENTITY_WIND_FACTOR: Final = "number.nbe_wind_factor"
ENTITY_CALORIFIC: Final = "input_number.nbe_pellet_calorific_mj"
ENTITY_PELLET_PRICE: Final = "number.nbe_pellet_price"
ENTITY_PELLET_TOTAL: Final = "sensor.nbe_pellet_total_consumption"

# --- WEWNĘTRZNE ID SENSORÓW ---
SENSOR_HOUSE_EFFICIENCY: Final = "sensor.nbe_house_efficiency"
SENSOR_OFFICE_EFFICIENCY: Final = "sensor.nbe_extra_efficiency"
SENSOR_HOPPER_CONTENT: Final = "sensor.nbe_hopper_content"

# --- KONFIGURACJA FIZYCZNA ---
DEFAULT_CALORIFIC_MJ: Final = 17.5
SPECIFIC_HEAT_WATER_KWH: Final = 0.00116  # kWh/kg*K
PELLET_CALORIFIC_KWH: Final = 4.8         # kWh z 1 kg
BOILER_EFFICIENCY_DHW: Final = 0.85       # Sprawność grzania CWU
TANK_VOLUME_LITERS_DEFAULT: Final = 200.0

# --- MAPOWANIE STANÓW STEROWNIKA (Przywrócone Twoje) ---
STOKER_STATES: Final = {
    "state_0": "Wyłączony",
    "state_2": "Rozpalanie_1",
    "state_4": "Rozpalanie_2",
    "state_5": "Praca",
    "state_6": "Modulacja",
    "state_7": "CWU",
    "state_9": "Postój",
    "state_14": "Wyłączony",
    "state_20": "Brak pelletu",
    "state_43": "Czyszczenie",
    "state_99": "Błąd",
}

STOKER_INFO: Final = {                                  
    20: "B....d zap..onu",                              
    21: "Wysoka temperatura kot..a",                          
    22: "Zatrzymanie zewn..trzne",                           
    23: "Niski poziom pelletu",                                
    24: "Wymagane czyszczenie",                                   
    25: "B....d czujnika powrotu",                                        
    26: "Ochrona przed mrozem",                     
    27: "B....d komunikacji",                                   
    28: "Pojemnik na popi.... pe..ny"                 
}                                                                 

CWU_MODES: Final = ["CWU", "Hot Water", "Grzanie wody", "state_7"]

# --- KONFIGURACJA BINARY I OUTPUT ---
BINARY_SENSORS_CONFIG = [
    ("boiler_running", "Kocioł w pracy", "miscdata.state.value", None),
    ("boiler_alarm", "Alarm", "miscdata.alarm.value", BinarySensorDeviceClass.PROBLEM),
]

OUTPUT_SENSORS_CONFIG = [
    ("output-1", "Pompa CWU", "mdi:water-boiler", "dhw_pump"),
    ("output-2", "Pompa Kotła", "mdi:pump", "boiler_pump"),
    ("output-4", "Pompa Pogodowa 1", "mdi:heating-coil", "weather_pump_1"),
    ("output-9", "Pompa Pogodowa 2", "mdi:heating-coil", "weather_pump_2"),
]

WEATHER_ZONE_TRANSLATIONS = {
    "temp": "Temperatura aktualna", 
    "wanted": "Temperatura zadana", 
    "return": "Temperatura powrotu", 
    "external": "Temperatura zewnętrzna",
    "active": "Status strefy"
}

SIMPLE_NUMBERS_CONFIG = [
    ("pellet_price", "Cena pelletu", 500, 5000, 10, "PLN/t", "mdi:cash", 1250),
    ("comfort_temperature", "Temperatura komfortu", 15, 28, 0.5, UnitOfTemperature.CELSIUS, "mdi:thermometer-lines", 22),
    ("extra_building_target_temp", "Temperatura Biura", 5, 25, 0.5, UnitOfTemperature.CELSIUS, "mdi:office-building-marker", 15),
    ("wind_factor", "Współczynnik wiatru", 0, 20, 1, PERCENTAGE, "mdi:wind-power", 5),
    ("dhw_tank_volume", "Pojemność bojlera", 50, 1000, 10, "l", "mdi:barrel", 200),
    ("system_efficiency", "Sprawność grzania CWU", 10, 100, 1, PERCENTAGE, "mdi:gauge", 85),
    ("anomaly_threshold", "Anomalia wydajności", 5, 100, 5, PERCENTAGE, "mdi:alert-percent", 20),
]

SENSOR_MAP: Final = [
    ("Zegar kotła", "boiler_clock", "miscdata.clock.value", None, None, None, "mdi:clock", None),
    ("Status kotła", "boiler_status", "miscdata.state.value", None, None, None, "mdi:heating-coil", {
        "status_raw": "miscdata.state.value"
    }),
    ("Temperatura kotła", "boiler_temp", "frontdata.boilertemp", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, "mdi:thermometer", {
        "target": "boilerdata.2"
    }),
    ("Temperatura powrotu", "return_temperature", "boilerdata.17", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, "mdi:thermometer-minus", None),
    ("Temperatura spalin", "smoke_temperature", "frontdata.smoketemp", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, "mdi:fire-alert", None),
    ("Temperatura CWU", "dhw_temperature", "frontdata.dhw", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, "mdi:water-boiler", {
        "dhw_temperature_requested": "frontdata.dhwwanted",
        "dhw_low_temperature": "dhwdata.8",
        "dhw_hysteresis": "dhwdata.3"
    }),
    ("Konsumpcja dzienna", "consumption_today", "stats.day", UnitOfMass.KILOGRAMS, SensorDeviceClass.WEIGHT, SensorStateClass.TOTAL, "mdi:chart-bell-curve", None),
    ("Pellet w zasobniku", "hopper_content", "frontdata.hoppercontent", UnitOfMass.KILOGRAMS, SensorDeviceClass.WEIGHT, SensorStateClass.MEASUREMENT, "mdi:tray-full", None),
    ("Poziom tlenu", "oxygen_current", "boilerdata.12", PERCENTAGE, None, SensorStateClass.MEASUREMENT, "mdi:molecule-os", {
        "oxygen_reference": "frontdata.oxyr"
    }),
    ("Ciśnienie zwrotne", "backpressure", "miscdata.backpressure", "Pa", None, SensorStateClass.MEASUREMENT, "mdi:gauge", None),
    ("Aktualna moc", "current_power", "boilerdata.5", UnitOfPower.KILO_WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "mdi:flash", {
        "power_pct": "boilerdata.4",
        "ash_distance": "frontdata.ashdist"
    }),
    ("Statystyki zasobnika", "hopper_statistics", "hopperdata.1", UnitOfMass.KILOGRAMS, SensorDeviceClass.WEIGHT, SensorStateClass.MEASUREMENT, "mdi:database-import", {
        "counter_1": "hopperdata.5",
        "counter_2": "hopperdata.13",
        "consumption_24h": "hopperdata.3",
        "total_pellet_burned": "hopperdata.4",
        "feeder_performance": "hopperdata.2"
    }),
    ("Całkowite zużycie pelletu", "consumption_statistics", "hopperdata.4", UnitOfMass.KILOGRAMS, SensorDeviceClass.WEIGHT, SensorStateClass.TOTAL_INCREASING, "mdi:sigma", {
        "current_hour": "stats.current_hour",
        "previous_hour": "stats.previous_hour",
        "today": "stats.day",
        "yesterday": "stats.yesterday",
        "dhw_today": "stats.dhw_day",
        "month": "stats.month",
        "year": "stats.year"
    }),
    ("Pogoda StokerCloud", "weather_stokercloud", "weatherdata.weather-city", None, None, None, "mdi:weather-partly-cloudy", {
        "outdoor_temp": "weatherdata.1",
        "wind_speed": "weatherdata.2",
        "wind_direction": "weatherdata.3",
        "humidity": "weatherdata.4",
        "pressure": "weatherdata.5",
        "cloud_cover": "weatherdata.9"
    }),
    ("Zużycie pelletu CWU dzisiaj", "dhw_consumption_today", "stats.dhw_day", UnitOfMass.KILOGRAMS, SensorDeviceClass.WEIGHT, SensorStateClass.TOTAL, "mdi:water-boiler-auto", None)
]
