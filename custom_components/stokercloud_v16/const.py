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
DOMAIN: Final = "stokercloud_v16"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"

# --- ZEWNĘTRZNE ENCJE (ZALEŻNOŚCI) ---
ENTITY_WEATHER: Final = "sensor.nbe_weather_stokercloud"
ENTITY_BOILER_STATUS: Final = "sensor.nbe_boiler_status"
ENTITY_PUMP_HOUSE: Final = "binary_sensor.nbe_weather_pump_1"
ENTITY_PUMP_OFFICE: Final = "binary_sensor.nbe_weather_pump_2"
ENTITY_SWITCH_OFFICE: Final = "switch.nbe_office_logic"
ENTITY_OFFICE_TIME_SHIFT: Final = "number.nbe_office_time_shift"
ENTITY_TEMP_TARGET_HOUSE: Final = "number.nbe_home_target_temp"
ENTITY_TEMP_TARGET_OFFICE: Final = "number.nbe_office_target_temp"
ENTITY_WIND_FACTOR: Final = "number.nbe_wind_factor"
ENTITY_INSULATION_FACTOR_HOUSE: Final = "number.nbe_insulation_factor_house"
ENTITY_DHW_TANK_VOLUME: Final = "number.nbe_dhw_tank_volume"
ENTITY_CALORIFIC: Final = "input_number.nbe_pellet_calorific_mj"
ENTITY_PELLET_PRICE: Final = "number.nbe_pellet_price"
ENTITY_PELLET_TOTAL: Final = "sensor.nbe_pellet_total_consumption"
ENTITY_HOUSE_CONSUMPTION_DAILY: Final = "sensor.nbe_house_consumption_daily"
ENTITY_OFFICE_CONSUMPTION_DAILY: Final = "sensor.nbe_office_consumption_daily"


# --- WEWNĘTRZNE ID SENSORÓW ---
SENSOR_HOUSE_EFFICIENCY: Final = "sensor.nbe_house_efficiency"
SENSOR_OFFICE_EFFICIENCY: Final = "sensor.nbe_office_efficiency"
SENSOR_HOPPER_CONTENT: Final = "sensor.nbe_hopper_content"
SENSOR_DHW_TEMPERATURE: Final = "sensor.nbe_dhw_temperature"
SENSOR_FORECAST_TOTAL_WEIGHT: Final = "sensor.nbe_forecast_total_weight"

# --- KONFIGURACJA FIZYCZNA ---
DEFAULT_CALORIFIC_MJ: Final = 18.0
SPECIFIC_HEAT_WATER_KWH: Final = 0.00116  # kWh/kg*K
PELLET_CALORIFIC_KWH: Final = 4.8         # kWh z 1 kg
BOILER_EFFICIENCY_DHW: Final = 0.85       # Sprawność grzania CWU
TANK_VOLUME_LITERS_DEFAULT: Final = 200.0

# --- MAPOWANIE STANÓW STEROWNIKA (Przywrócone Twoje) ---
STOKER_STATES: Final = {
    "state_0": "ZACZEKAJ",
    "state_1": "WŁĄCZ",
    "state_2": "ROZPALANIE_1",
    "state_4": "ROZPALANIE_2",
    "state_5": "PRACA",
    "state_7": "CWU",
    "state_8": "BŁĄD TEMP. KOTŁA",
    "state_9": "ZATRZYMANIE-TEMP.OSIĄGNIĘTA",
    "state_11": "ALARM PALNIKA-PRZEGRZANIE",
    "state_12": "ODŁĄCZONA WTYCZKA",
    "state_13": "NIEUDANE ROZPALANIE",
    "state_14": "WYŁĄCZONY",
    "state_15": "BŁĄD CZUJNIKA KOTŁA",
    "state_17": "BŁĄD CZUJNIKA PALNIKA",
    "state_19": "BŁĄD ŚLIMAKA-WYJŚCIE L1",
    "state_20": "BŁĄD-BRAK OGNIA",
    "state_22": "ZATRZYMANIE-TEMP. ZEWNĘTRZNĄ",
    "state_23": "ZATRZYMANIE-HARMONOGRAM",
    "State_24": "ZATRZYMANIE-TERMOSTAT",
    "state_25": "ZATRZYMANIE-KOMPENSACJA POGODOWA",
    "state_29": "ALRAM-PRZEGRZANIE",
    "state_31": "BŁĄD KOMPRESORA",
    "state_36": "ALARM-WYSOKIE CIŚNIENIE ZWROTNE",
    "state_37": "BŁĄD NADMUCHU",
    "state_38": "ZA WYSOKA TEMP. NA WYJ.",
    "state_39": "POPILENIK NIE PODŁĄCZONY",
    "state_41": "ALARM-ZASOBNIK PELLETU",
    "state_42": "BŁĄD SONDY LAMBDA",
    "state_43": "CZYSZCZENIE KOMPRESOREM",
    "state_44": "USZKODZENIE ZAPALARKI",
    "state_45": "BŁĄD CZUJNIKA ZASOBNIKA",
    "state_46": "ZATRZYMANIE-PUSTY ZASOBNIK",
    "state_49": "ZA NISKA TEMP. NA WYJ.",
    "state_50": "BŁĄD WENTYLATORA"
}

STOKER_INFO: Final = {
    2: "Niski poziom tlenu, pellet zablokowany",
    4: "Brak światła na fotoczujniku przez ponad 1 minutę",
    9: "Nowa wiadomość na Stokercloud.dk",
    10: "Moc ograniczona przez kompensację pogodową",
    14: "Brak połączenia z modułem rozszerzeń",
    21: "Awaryjne schładzanie solarów, błąd czujnika temperatury",
    22: "Przegrzanie solarów",
    23: "Niski poziom pelletu w zasobniku",
    25: "Moc ograniczona przez wysoką temperaturę powietrza",
    26: "Błąd czujnika temperatury pokojowej",
    27: "Błąd czujnika temp. spalin T2",
    28: "Błąd czujnika temp. wylotowej T3",
    29: "Błąd czujnika zasilania strefy 1 (pogodówka)",
    30: "Błąd czujnika odniesienia strefy 1 (pogodówka)",
    31: "Błąd czujnika zasilania strefy 2 (pogodówka)",
    32: "Błąd czujnika odniesienia strefy 2 (pogodówka)",
    33: "Błąd czujnika temperatury CWU T4",
    34: "Błąd czujnika temperatury powrotu T3",
    35: "Błąd czujnika temperatury paneli solarnych 1",
    36: "Błąd czujnika temperatury paneli solarnych 2",
    37: "Błąd dolnego czujnika temperatury zasobnika solarnego",
    38: "Błąd czujnika temperatury przegrzania solarów",
    39: "Czyszczenie kotła zablokowane przez harmonogram",
    40: "Alarm podajnika: Czujnik poziomu poza zakresem",
    41: "Alarm podajnika: Brak przyrostu paliwa",
    42: "Błąd transportu pneumatycznego zresetowany przez użytkownika",
    43: "Popielnik pełny - wymaga opróżnienia!",
    44: "Kontakt popielnika przełączony (On/Off)",
    45: "Wysokie ciśnienie zwrotne - redukcja pelletu, wentylator 100%",
    46: "Ciśnienie zwrotne w normie",
    48: "Podawanie zewnętrzne uruchomione",
    49: "Podawanie zewnętrzne zatrzymane",
    50: "Urządzenie chłodzące w stanie zatrzymania/błędu",
    52: "Moc ograniczona przez zmniejszony przepływ powietrza",
    53: "Moc ograniczona przez brak podciśnienia w kotle",
    60: "Anty-stop pompy kotłowej",
    61: "Anty-stop pompy pogodowej 1",
    62: "Anty-stop pompy pogodowej 2",
    63: "Anty-stop pompy solarów",
    64: "Błąd podczas czyszczenia",
    69: "Stabilizacja płomienia włączona",
    70: "Stabilizacja płomienia wyłączona",
    73: "Przywrócono pełną moc (przepływ powietrza OK)",
    74: "Kompensacja pogodowa ograniczona przez temp. powrotu",
    75: "Kompensacja pogodowa - powrót OK",
    76: "Przywrócono pełną moc (podciśnienie OK)",
    77: "Wydajność podajnika przywrócona (sprzed 3h)",
    80: "Błąd czujnika zasilania strefy 3 (pogodówka)",
    81: "Błąd czujnika odniesienia strefy 3 (pogodówka)",
    82: "Błąd czujnika zasilania strefy 4 (pogodówka)",
    83: "Błąd czujnika odniesienia strefy 4 (pogodówka)",
    84: "Anty-stop pompy pogodowej 3",
    85: "Anty-stop pompy pogodowej 4",
    86: "Wymagana kalibracja czujnika tlenu!",
    87: "Oczekiwanie na start",
    88: "Podajnik zewnętrzny blokowany przez czyszczenie kompresorem",
    89: "Moc kW zredukowana o określoną wartość",
    90: "Zatrzymanie przez ceny energii (pre-stop)",
    91: "Zatrzymanie przez ceny energii",
    92: "Wymuszenie mocy (Forced Power)",
    93: "Zatrzymanie przez temperaturę zewnętrzną",
    94: "Zatrzymanie przez własną produkcję (PV)",
    95: "Błąd temperatury pokojowej - powrót do T1",
    96: "Błąd czujnika temperatury zewnętrznej",
    97: "Czyszczenie komina - zadana 70 stopni, kompresor wyłączony",
    98: "Test wentylatora zakończony",
    99: "Filtr elektrostatyczny aktywny",
    100: "Filtr elektrostatyczny aktywacja za...",
    101: "Przekroczenie parametrów filtra elektrostatycznego",
    102: "Filtr elektrostatyczny zatrzymany - brak podciśnienia",
    103: "Niski poziom tlenu, blokada pelletu za...",
    104: "Niski poziom tlenu, odliczanie zakończone",
    110: "Błąd podciśnienia: Wentylator wyciągowy uszkodzony/wyłączony",
    111: "Błąd podciśnienia: Wentylator wyciągowy zablokowany",
    112: "Błąd silnika odpopielania: Odłączona wtyczka/uszkodzenie",
    113: "Błąd silnika odpopielania: Silnik zablokowany/kocioł zapchany",
    114: "Błąd podciśnienia: Uszkodzony wąż gumowy",
    115: "Błąd podciśnienia: Zablokowany wąż/kocioł/komin",
    116: "Błąd modułu podciśnienia",
    117: "Błąd przepływu: Odłączona wtyczka/uszkodzona dmuchawa",
    118: "Błąd przepływu: Dmuchawa zablokowana lub uszkodzona",
    119: "Błąd przepływu: Uszkodzony lub zatkany wąż pomiarowy",
    120: "Błąd przepływu: Zabrudzony filtr lub uszkodzony moduł",
    121: "Błąd modułu przepływu powietrza"
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

# Konfiguracja Wyjść (Outputs)
STOKER_OUTPUTS_CONFIG = [
    ("output-3", "Zawór pogodowy", "mdi:valve", "%"),
    ("output-5", "Wentylator wyciągowy", "mdi:fan", "%"),
    ("output-7", "Czyszczenie kotła", "mdi:broom", "kg"),
    ("output-6", "Odpopielanie", "mdi:trash-can", None),
]

# Konfiguracja Menu Ustawień
STOKER_SETTINGS_MENU_CONFIG = [
    ("Ustawienia Kotła", "boiler", "mdi:format-list-bulleted-type"),
    ("Ustawienia CWU", "hot_water", "mdi:water-boiler"),
    ("Ustawienia Regulacji", "regulation", "mdi:tune"),
    ("Ustawienia Nadmuchu", "fan", "mdi:fan"),
    ("Ustawienia Tlenu", "oxygen", "mdi:fire"),
    ("Ustawienia Czyszczenia", "cleaning", "mdi:broom"),
    ("Ustawienia Zasobnika", "hopper", "mdi:tray-full"),
    ("Ustawienia Pogodowe", "weather", "mdi:weather-partly-cloudy"),
]

WEATHER_ZONE_TRANSLATIONS = {
    "actual": "current_flow_temp", 
    "wanted": "wanted_flow_temp", 
    "calc": "avarage_temp",
    "actualref": "current_temp",
    "valve": "valve_position",
    "active": "zone_active"
}

SIMPLE_NUMBERS_CONFIG = [
    ("pellet_price", "Cena pelletu", 500, 4000, 10, "PLN/t", "mdi:cash", 1250, "auto"),
    ("house_target_temp", "Temperatura zadana Domu", 15, 28, 0.5, UnitOfTemperature.CELSIUS, "mdi:thermometer-lines", 22, "auto"),
    ("office_target_temp", "Temperatura Zadana Biura", 5, 25, 0.5, UnitOfTemperature.CELSIUS, "mdi:office-building-marker", 10, "auto"),
    ("wind_factor", "Współczynnik wiatru", 0, 20, 1, PERCENTAGE, "mdi:wind-power", 5, "slider"),
    ("dhw_tank_volume", "Pojemność bojlera", 50, 1000, 10, "l", "mdi:barrel", 200, "box"),
    ("system_efficiency", "Sprawność grzania CWU", 10, 100, 1, PERCENTAGE, "mdi:gauge", 85, "slider"),
    ("anomaly_threshold", "Anomalia wydajności", 5, 100, 5, PERCENTAGE, "mdi:alert-circle", 20, "slider"),
    ("office_time_shift", "Czas stabilizacji biura", 0, 60, 1, "min", "mdi:timer-sand", 10, "slider"),                              
    ("insulation_factor_house", "Charakterystyka strat - Dom", 0.05, 2, 0.01, "kg/°C/24h", "mdi:home-thermometer-outline", 0.6, "auto"),                                    
    ("insulation_factor_office", "Charakterystyka strat - Biuro", 0.05, 2, 0.01, "kg/°C/24h", "mdi:home-thermometer-outline", 1.2, "auto"),
]

SENSOR_MAP: Final = [
    ("Zegar kotła", "boiler_clock", "miscdata.clock.value", None, None, None, "mdi:clock", None),
    ("Status kotła", "boiler_status", "miscdata.state.value", None, None, None, "mdi:heating-coil", {
        "status_raw": "miscdata.state.value"
    }),
    ("Temperatura kotła", "boiler_temp", "frontdata.boilertemp", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, "mdi:thermometer", {
        "target": "frontdata.-wantedboilertemp"
    }),
    ("Temperatura powrotu", "return_temperature", "boilerdata.17", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, "mdi:thermometer-minus", None),
    ("Temperatura spalin", "smoke_temperature", "frontdata.smoketemp", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, "mdi:fire-alert", None),
    ("Temperatura CWU", "dhw_temperature", "frontdata.dhw", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, "mdi:water-boiler", {
        "dhw_temperature_requested": "frontdata.dhwwanted",
        "dhw_low_temperature": "dhwdata.8",
        "dhw_hysteresis": "dhwdata.3"
    }),
    ("Konsumpcja dzienna", "consumption_today", "stats.day", UnitOfMass.KILOGRAMS, SensorDeviceClass.WEIGHT, SensorStateClass.TOTAL, "mdi:chart-bell-curve", None),
    ("Pellet w zasobniku", "hopper_content", "frontdata.hoppercontent", UnitOfMass.KILOGRAMS, SensorDeviceClass.WEIGHT, SensorStateClass.MEASUREMENT, "mdi:tray-full", {
        "hopper_distance": "frontdata.hopperdistance"
    }),
    ("Poziom tlenu", "oxygen_current", "boilerdata.12", PERCENTAGE, None, SensorStateClass.MEASUREMENT, "mdi:fire-circle", {
        "oxygen_reference": "frontdata.refoxygen"
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
    ("Zużycie pelletu CWU dzisiaj", "dhw_consumption_today", "stats.dhw_day", UnitOfMass.KILOGRAMS, SensorDeviceClass.WEIGHT, SensorStateClass.TOTAL, "mdi:water-boiler-auto", None),
    ("Informacja", "boiler_info", "infomessages", None, None, None, "mdi:information", None)
]
