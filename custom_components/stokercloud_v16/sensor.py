from __future__ import annotations
import logging
import time
from datetime import datetime, timedelta
from .entity import StokerEntity
from homeassistant.util import dt as dt_util
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfPower,
    UnitOfTemperature,
    UnitOfMass,
    PERCENTAGE,
    EntityCategory,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
# Poprawiony import dla zdarzeń
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.sensor import ENTITY_ID_FORMAT                                                                        
from .const import (
    DOMAIN,
    ENTITY_SWITCH_OFFICE,
    ENTITY_TEMP_TARGET_HOUSE,
    ENTITY_TEMP_TARGET_OFFICE,
    ENTITY_OFFICE_TIME_SHIFT,
    ENTITY_PELLET_PRICE,
    ENTITY_PUMP_HOUSE,
    ENTITY_PUMP_OFFICE,
    ENTITY_WIND_FACTOR,
    ENTITY_BOILER_STATUS,
    ENTITY_HOUSE_CONSUMPTION_DAILY,
    ENTITY_OFFICE_CONSUMPTION_DAILY,
    ENTITY_DHW_TANK_VOLUME,
    ENTITY_INSULATION_FACTOR_HOUSE,
    SENSOR_HOUSE_EFFICIENCY,
    SENSOR_OFFICE_EFFICIENCY,
    SENSOR_FORECAST_TOTAL_WEIGHT,
    SENSOR_DHW_TEMPERATURE,
    BOILER_EFFICIENCY_DHW,
    SPECIFIC_HEAT_WATER_KWH,
    PELLET_CALORIFIC_KWH,
    STOKER_STATES,
    STOKER_INFO,
    SENSOR_MAP,
    STOKER_OUTPUTS_CONFIG,
    STOKER_SETTINGS_MENU_CONFIG
)

_LOGGER = logging.getLogger(__name__)

# --- BASE SENSOR ---
class StokerSensor(StokerEntity, SensorEntity):
    """Jeden sensor, by wszystkimi rządzić. Obsługuje ścieżki, jednostki i atrybuty."""
    
    def __init__(self, coordinator, username, name, uid, path, unit=None, dev_class=None, state_class=None, icon=None, attrs=None):
        super().__init__(coordinator, username)
        self._attr_name = name
        self._attr_unique_id = f"nbe_{username}_{uid}"
        self.entity_id = f"sensor.nbe_{uid}"
        self._path = path
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = dev_class
        self._attr_state_class = state_class
        self._attr_icon = icon
        self._attrs_map = attrs or {}

    def _resolve_path(self, path):
        """Pomocnik do wyciągania danych ze słownika po ścieżce 'klucz.podklucz'."""
        val = self.coordinator.data
        if not val:
            return None
        for key in path.split('.'):
            if isinstance(val, dict):
                val = val.get(key)
            else:
                return None
        return val

    @property
    def native_value(self):
        val = self._resolve_path(self._path)
        
        if isinstance(val, list):
            val = val[0] if len(val) > 0 else None

        # Logika mapowania stanu dla głównego sensora statusu
        if self._attr_unique_id.endswith("boiler_status"):
            if val is None: return "Nieznany"
            raw = str(val).replace("lng_", "")
            return STOKER_STATES.get(raw, raw)
        elif self._attr_unique_id.endswith("boiler_info"):                                                                      
            if val is None or val == "" or val == "0" or val ==0:
                return "OK"
            try:
                raw_info = int(val)   
                return STOKER_INFO.get(raw_info, raw_info)
            except (ValueError, TypeError):
                return str(val)

        # Uniwersalna konwersja na float (obsługuje kropki i przecinki)
        if val is not None:
            try:
                if isinstance(val, str):
                    val = val.replace(",", ".")
                return float(val)
            except (ValueError, TypeError):
                pass
        return val

    @property
    def extra_state_attributes(self):
        res = {}
        for k, p in self._attrs_map.items():
            attr_val = self._resolve_path(p)
            res[k] = attr_val
        return res


# --- DHW EFFICIENCY SENSOR ---
class StokerDHWEfficiencySensor(StokerEntity, SensorEntity):
    """Sensor monitorujący wydajność i czas grzania CWU (Ciepłej Wody Użytkowej)."""

    def __init__(self, coordinator, username):
        """Inicjalizacja sensora procesowego CWU."""
        super().__init__(coordinator, username)
        
        self.entity_id = "sensor.nbe_dhw_heating_time"
        self._attr_name = "Ostatni czas grzania CWU"
        self._attr_unique_id = f"nbe_{username}_dhw_heat_time"
        self._attr_icon = "mdi:timer-outline"
        
        # Stan wewnętrzny do obliczeń
        self._start_time: datetime | None = None
        self._start_pellet: float = 0.0
        self._last_duration_min: float = 0.0
        self._last_pellet_used: float = 0.0
        self._is_heating: bool = False

    def _handle_coordinator_update(self) -> None:
        """Logika wykrywania cyklu grzania przy aktualizacji danych."""
        # Pobieramy status wyjścia (pompy/zaworu CWU)
        # Wykorzystujemy bazowe _get_api_data dla bezpieczeństwa
        status_val = self._get_api_data("leftoutput.output-1.val")
        is_on = str(status_val).upper() == "ON"
        
        # Pobieramy licznik pelletu
        try:
            current_total = float(str(self._get_api_data("hopperdata.4") or 0).replace(",", "."))
        except (ValueError, TypeError):
            current_total = 0.0
                                                                                                 
        # Wykrycie początku grzania
        if is_on and not self._is_heating:
            self._start_time = datetime.now()
            self._start_pellet = current_total
            self._is_heating = True
        
        # Wykrycie końca grzania
        elif not is_on and self._is_heating:
            if self._start_time:
                duration = (datetime.now() - self._start_time).total_seconds() / 60
                self._last_duration_min = round(duration, 1)
                self._last_pellet_used = max(0.0, round(current_total - self._start_pellet, 2))
            self._is_heating = False
            self._start_time = None

        # Powiadomienie HA o zmianie stanu
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        """Zwraca czas w formacie HH:MM (aktualny lub ostatni zakończony)."""
        total_min = 0
        if self._is_heating and self._start_time:
            total_min = int((datetime.now() - self._start_time).total_seconds() / 60)
        else:
            total_min = int(self._last_duration_min)

        h, m = divmod(max(0, total_min), 60)
        return f"{h:02}:{m:02}"

    @property
    def extra_state_attributes(self):
        """Dodatkowe informacje o sesji grzania."""
        return {
            "heating_status": "ON" if self._is_heating else "OFF",
            "last_cycle_consumption_kg": self._last_pellet_used,
            "current_session_start": self._start_time.isoformat() if self._start_time else None,
            "unit": "minut"
        }


# --- HOUSE & OFFICE EFFICIENCY SENSOR ---
class StokerEfficiencySensor(StokerEntity, SensorEntity, RestoreEntity):
    def __init__(self, coordinator, username, name, uid, consumption_sid, target_temp_sid, attr_name=None, use_wind=False, *args, **kwargs):
        super().__init__(coordinator, username)
        self.entity_id = f"sensor.nbe_{uid}_efficiency"
        self._attr_name = f"{name} - Indeks efektywności"
        self._attr_unique_id = f"nbe_{username}_{uid}_efficiency"
        self._attr_native_unit_of_measurement = "kg/°C/24h"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:chart-bell-curve-cumulative"
        
        self._uid = uid 
        self._consumption_sid = consumption_sid 
        self._target_temp_sid = target_temp_sid 
        self._attr_name_source = attr_name                
        self._use_wind = use_wind
        
        self._last_consumption_val = None
        self._last_calc_time = None
        self._current_efficiency = 0.8  
        self._office_start_timestamp = None
        self._office_last_pump_on_time = None 

        self._alpha = 0.1  
        self._instant_kg_per_hour = 0.0
        self._diag_house_share = 0.0
        self._diag_office_share = 0.0
        self._debug_pump_state = "off"
        self._dynamic_limit_cache = 20.0

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            if last_state.state not in ["unknown", "unavailable"]:
                try: self._current_efficiency = float(last_state.state)
                except ValueError: pass
            old_ts = last_state.attributes.get("office_start_ts")
            if old_ts: self._office_start_timestamp = float(old_ts)

    @property
    def native_value(self):
        return round(self._current_efficiency, 3)

    @property
    def extra_state_attributes(self):
        now = time.time()
        pump_on = (self._debug_pump_state == "on")
        elapsed_min = (now - self._office_start_timestamp) / 60 if self._office_start_timestamp else 0
        time_left = max(0, self._dynamic_limit_cache - elapsed_min) if pump_on and elapsed_min < self._dynamic_limit_cache else 0

        return {
            "burn_rate_total_kg_h": round(self._instant_kg_per_hour, 3),
            "assigned_to_house_kg_h": round(self._diag_house_share, 3),
            "assigned_to_office_kg_h": round(self._diag_office_share, 3),
            "office_heating_active": pump_on,
            "time_shift_active": pump_on and (0 < elapsed_min < 20),
            "time_shift_elapsed_min": round(elapsed_min, 1) if pump_on else 0,
            "time_shift_limit_min": round(self._dynamic_limit_cache, 1),
            "time_shift_remaining_min": round(time_left, 1),
            "office_start_time": datetime.fromtimestamp(self._office_start_timestamp).strftime('%d-%m-%Y %H:%M:%S') if self._office_start_timestamp else "Nieaktywne"
        }

    def _handle_coordinator_update(self) -> None:
        try:
            now = time.time()
            
            # 1. POMPY I CZAS
            sw_biuro = self.hass.states.get(ENTITY_SWITCH_OFFICE)
            pump_biuro = self.hass.states.get(ENTITY_PUMP_OFFICE)
            switch_is_on = (sw_biuro.state != "off") if sw_biuro else True
            pump_is_on = (pump_biuro and pump_biuro.state == "on")
            self._debug_pump_state = "on" if pump_is_on else "off"

            if switch_is_on and pump_is_on:
                self._office_last_pump_on_time = now
                if not self._office_start_timestamp: self._office_start_timestamp = now
            elif not switch_is_on:
                self._office_start_timestamp = None
            elif not pump_is_on and self._office_start_timestamp:
                if self._office_last_pump_on_time and (now - self._office_last_pump_on_time) > 600:
                    self._office_start_timestamp = None

            # 2. POGODA I PROGNOZY (Zawsze aktualne)
            t_state = self.hass.states.get(self._target_temp_sid)
            temp_target = float(t_state.state) if t_state and t_state.state not in ["unknown", "unavailable"] else 22.0
            wd = (self.coordinator.data or {}).get("weatherdata", {})
            try:
                temp_ext = float(str(wd.get("1", 0)).replace(",", "."))
            except:
                temp_ext = 0.0
           
            shift_entity = self.hass.states.get(ENTITY_OFFICE_TIME_SHIFT)                                                       
            base_shift = float(shift_entity.state) if shift_entity and shift_entity.state not in ["unknown", "unavailable"] else 10.0
            temp_adjustment = max(0, (10.0 - temp_ext) / 5.0) * 4.0                                                             
            self._dynamic_limit_cache = base_shift + temp_adjustment                                                                  
 
            delta_t = max(1.0, temp_target - temp_ext)
            effective_delta = delta_t
            if self._use_wind:
                try:
                    wind_speed = float(str(wd.get("2", 0)).replace(",", "."))
                    wind_factor_state = self.hass.states.get(ENTITY_WIND_FACTOR)
                    wind_factor = (float(wf_state.state) / 100.0) if wind_factor_state else 0.05
                    effective_delta = delta_t * (1 + (wind_speed * wind_factor))
                except: pass

            # Indeksy do podziału proporcjonalnego
            house_eff_sensor = self.hass.states.get(SENSOR_HOUSE_EFFICIENCY)
            idx_house = float(house_eff_sensor.state) if house_eff_sensor and house_eff_sensor.state not in ["unknown", "unavailable"] else 0.62
            
            # PROGNOZOWANE zapotrzebowanie (ile strefa "chciałaby" spalić)
            pred_house = (idx_house * effective_delta) / 24.0
            pred_office = (self._current_efficiency * effective_delta) / 24.0

            # 3. SPALANIE (Blokada 5 min)
            state_obj = self.hass.states.get(self._consumption_sid)
            if not state_obj or state_obj.state in ["unknown", "unavailable"]: return

            try: current_kg = float(state_obj.attributes.get(self._attr_name_source, 0)) if self._attr_name_source else float(state_obj.state)
            except: return

            if self._last_consumption_val is None or current_kg < self._last_consumption_val:
                self._last_consumption_val = current_kg
                self._last_calc_time = now
                return

            time_diff_sec = now - self._last_calc_time
            if time_diff_sec < 300:
                # W czasie oczekiwania pokazujemy prognozę w atrybutach
                self._diag_house_share = pred_house
                self._diag_office_share = pred_office
                self.async_write_ha_state()
                return

            delta_kg = current_kg - self._last_consumption_val
            self._instant_kg_per_hour = delta_kg / (time_diff_sec / 3600.0) if delta_kg > 0.005 else 0.0

            # 4.ZAMROŻENIE INDEKSU PODCZAS CWU (Przywrócone) ---
            boiler_status = self.hass.states.get(ENTITY_BOILER_STATUS)
            if boiler_status and boiler_status.state in ["CWU", "state_7"]:
                self._last_consumption_val = current_kg
                self._last_calc_time = now
                self._diag_house_share = pred_house
                self._diag_office_share = pred_office
                self.async_write_ha_state()
                return

            # 5. INTELIGENTNY ROZDZIAŁ
            is_office_active = (switch_is_on and pump_is_on)
            elapsed = (now - self._office_start_timestamp) / 60 if self._office_start_timestamp else 0
            is_office_reliable = is_office_active and elapsed >= self._dynamic_limit_cache
            
            new_instant_eff = self._current_efficiency
            do_math_update = False

            if self._uid == "house":
                if not is_office_reliable:
                    self._diag_house_share = self._instant_kg_per_hour
                    self._diag_office_share = pred_office
                    new_instant_eff = (self._instant_kg_per_hour * 24.0) / effective_delta
                    do_math_update = True
                else:
                    # PROPORCJA: Jeśli obie strefy grzeją, dzielimy spalanie wg potrzeb
                    total_pred = pred_house + pred_office
                    self._diag_house_share = self._instant_kg_per_hour * (pred_house / total_pred)
                    self._diag_office_share = self._instant_kg_per_hour * (pred_office / total_pred)

            elif self._uid == "office":
                if is_office_reliable:
                    total_pred = pred_house + pred_office
                    # Biuro dostaje swoją proporcjonalną część
                    office_kg_h = self._instant_kg_per_hour * (pred_office / total_pred)
                    self._diag_office_share = office_kg_h
                    self._diag_house_share = self._instant_kg_per_hour - office_kg_h
                    
                    new_instant_eff = (office_kg_h * 24.0) / effective_delta
                    do_math_update = True
                else:
                    self._diag_office_share = pred_office
                    self._diag_house_share = self._instant_kg_per_hour

            # 6. FINALIZACJA
            if do_math_update and 0.1 < new_instant_eff < 15.0:
                self._current_efficiency = (self._current_efficiency * (1 - self._alpha)) + (new_instant_eff * self._alpha)
            
            self._last_consumption_val = current_kg
            self._last_calc_time = now
            self.async_write_ha_state()

        except Exception as e:
            _LOGGER.error("Błąd wydajności %s: %s", self._uid, e)
 

# --- EFFICENCY DEVIATION SENSOR ---
class StokerEfficiencyDeviationSensor(StokerEntity, SensorEntity):
    """Porównuje realny indeks wydajności z zadanym współczynnikiem izolacji."""

    def __init__(self, coordinator, username):
        super().__init__(coordinator, username)
        self._username = username
        self.entity_id = "sensor.nbe_insulation_deviation"
        self._attr_has_entity_name = True
        self._attr_name = "Odchylenie izolacji"
        self._attr_unique_id = f"nbe_{username}_insulation_deviation"
        self._attr_native_unit_of_measurement = "kg/°C/24h"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:slope-uphill"

    @property
    def native_value(self):
        # Wykorzystanie SENSOR_HOUSE_EFFICIENCY z const.py
        eff_state = self.hass.states.get(SENSOR_HOUSE_EFFICIENCY)
        # Suwak referencyjny (Twoje założenie jak dom powinien trzymać ciepło)
        ins_state = self.hass.states.get(ENTITY_INSULATION_FACTOR_HOUSE)
        
        if not eff_state or not ins_state or eff_state.state in ["unknown", "unavailable"]: 
            return 0.0
            
        try:
            # Różnica: Realny Index - Założony Index
            deviation = float(eff_state.state) - float(ins_state.state)
            return round(deviation, 3)
        except (ValueError, TypeError):
            return 0.0
    
    @property
    def extra_state_attributes(self):
        """Dynamiczne statusy dla łatwiejszej diagnostyki."""
        val = self.native_value or 0
        if val <= 0.05:
            status = "Optymalnie"
        elif 0.05 < val <= 0.2:
            status = "Zwiększone straty"
        elif 0.2 < val <= 0.5:
            status = "Wykryto nieszczelność / wietrzenie"
        else:
            status = "Krytyczne straty energii"
            
        return {
            "insulation_status": status,
            "recommendation": "Sprawdź okna/wentylację" if val > 0.2 else "Brak uwag"
        }


# --- UNIFIED FORECAST SENSOR ---
class StokerUnifiedForecastSensor(StokerEntity, SensorEntity):
    """
    Uniwersalny sensor prognozy (Dom/Biuro/CWU/Suma) w KG lub PLN.
    Integruje aktualne zużycie dobowe z prognozą zapotrzebowania na resztę dnia.
    """
    def __init__(self, coordinator, username, target="total", forecast_type="weight"):
        super().__init__(coordinator, username)
        self._username = username
        self._target = target        
        self._type = forecast_type    
        
        target_names = {
            "house": "Dom", 
            "office": "Biuro", 
            "dhw": "CWU", 
            "total": "Suma"
        }
        name_prefix = target_names.get(target, "Suma")
        
        # Konfiguracja tożsamości encji
        if self._type == "weight":
            self.entity_id = f"sensor.nbe_forecast_{target}_weight"
            self._attr_name = f"Prognoza - {name_prefix} (KG)"
            self._attr_native_unit_of_measurement = "kg"
            self._attr_device_class = SensorDeviceClass.WEIGHT
            self._attr_icon = "mdi:chart-line"
        else:
            self.entity_id = f"sensor.nbe_forecast_{target}_cost"
            self._attr_name = f"Prognoza {name_prefix} (PLN)"
            self._attr_native_unit_of_measurement = "PLN"
            self._attr_device_class = SensorDeviceClass.MONETARY
            self._attr_icon = "mdi:cash-multiple"

        self._attr_unique_id = f"nbe_{username}_forecast_{target}_{forecast_type}"
        self._attr_state_class = SensorStateClass.TOTAL
 
    def _get_attribute_safely(self, entity_id, attribute_name, default=0.0):
        state = self.hass.states.get(entity_id)
        if state and state.attributes:
            attr_value = state.attributes.get(attribute_name)
            if attr_value not in ["unknown", "unavailable", None]:
                try: return float(attr_value)
                except ValueError: return default
        return default

    @property
    def native_value(self):
        try:
            # --- 1. CZAS I POGODA ---
            now = datetime.now()
            minutes_passed_today = now.hour * 60 + now.minute
            hours_left_today = max(0, 1440 - minutes_passed_today) / 60.0
            
            weather_data = self.coordinator.data.get("weatherdata", {})
            try: 
                ext_temp = float(str(weather_data.get("1", 0)).replace(",", "."))
            except (ValueError, TypeError): 
                ext_temp = 0.0
            
            wind_factor = 1.0
            try:
                wind_speed = float(str(weather_data.get("2", 0)).replace(",", "."))
                wf_state = self.hass.states.get(ENTITY_WIND_FACTOR)
                w_val = (float(wf_state.state) / 100.0) if wf_state else 0.05
                wind_factor = 1.0 + (wind_speed * w_val)
            except: pass
 
            # --- 2. PARAMETRY I STAŁE ---
            # Używamy stałych z const.py (efektywność spalania dla wody)
            eff_energy_kg = PELLET_CALORIFIC_KWH * BOILER_EFFICIENCY_DHW

            # --- 3. DOM (HOUSE) ---
            target_house_temp = self._get_value_safely(ENTITY_TEMP_TARGET_HOUSE, 23.0)
            delta_house_temp = max(0, (target_house_temp - ext_temp) * wind_factor   )
            
            idx_house_eff = self._get_value_safely(SENSOR_HOUSE_EFFICIENCY, 0.8)
            consumed_house = self._get_value_safely(ENTITY_HOUSE_CONSUMPTION_DAILY, 0.0)
            
            # Prognoza Domu = To co już spalił + (indeks * delta_house_temp / 24h) * pozostały czas
            predicted_rem_house = (idx_house_eff * delta_house_temp / 24.0) * hours_left_today
            forecast_house_total = consumed_house + predicted_rem_house

            # --- 4. BIURO (OFFICE) ---
            sw_office = self.hass.states.get(ENTITY_SWITCH_OFFICE)
            is_office_on = sw_office and sw_office.state == "on"
            
            target_office_temp = self._get_value_safely(ENTITY_TEMP_TARGET_OFFICE, 18.0)
            delta_office_temp = max(0, (target_office_temp - ext_temp) * wind_factor)
            
            idx_office_eff = self._get_value_safely(SENSOR_OFFICE_EFFICIENCY, 0.6)
            consumed_office = self._get_value_safely(ENTITY_OFFICE_CONSUMPTION_DAILY, 0.0)
            
            predicted_rem_office = 0.0
            if is_office_on:
                predicted_rem_office = (idx_office_eff * delta_office_temp / 24.0) * hours_left_today
            
            forecast_office_total = consumed_office + predicted_rem_office

            # --- 5. CWU (DHW) ---
            data = self.coordinator.data or {}
            
            consumed_dhw = float(data.get("stats", {}).get("dhw_day", 0.0))
            target_temp_dhw = float(data.get("frontdata", {}).get("dhwwanted", 50.0))
            curr_temp_dhw = float(data.get("dhwdata", {}).get("8", 40.0))
            hysteresis = float(data.get("dhwdata", {}).get("3", 5.0))

            tank_vol = self._get_value_safely(ENTITY_DHW_TANK_VOLUME, 200.0)
            
            # Jeśli woda jest chłodniejsza niż zadana (histereza), liczmy koszt dogrzania
            temp_gap_dhw = max(0, (target_temp_dhw - curr_temp_dhw)) 
            
            needed_dhw_now_kg = 0.0

            # Jeśli temperatura spadła poniżej (zadana - histereza), grzanie CWU
            if curr_temp_dhw < (target_temp_dhw - hysteresis):
                energy_now_kwh = tank_vol * temp_gap_dhw * SPECIFIC_HEAT_WATER_KWH
                needed_dhw_now_kg = energy_now_kwh / eff_energy_kg
            
            # straty postojowe (58W bojlera + cyrkulacja okazjonalna)
            # 0.014 (bojler) + 0.006 (dodatek na cyrkulację) = 0.02 kg/h
            standby_loss_rate = 0.02  
            standby_loss_kg = hours_left_today * standby_loss_rate
            forecast_dhw_total = consumed_dhw + needed_dhw_now_kg + standby_loss_kg

            # --- 6. AGREGACJA WYNIKU ---
            if self._target == "house":
                res_kg = forecast_house_total
            elif self._target == "office":
                res_kg = forecast_office_total
            elif self._target == "dhw":
                res_kg = forecast_dhw_total
            else: # "total"
                res_kg = forecast_house_total + forecast_office_total + forecast_dhw_total

            # --- 7. KONWERSJA NA WALUTĘ LUB KG ---
            if self._type == "weight":
                return round(res_kg, 2)
            else:
                price_ton = self._get_value_safely(ENTITY_PELLET_PRICE, 1250.0)
                return round(res_kg * (price_ton / 1000.0), 2)

        except Exception as e:
            _LOGGER.error("Błąd prognozy Unified Forecast (%s): %s", self._target, e)
            return 0.0


# --- FORECAST SENSOR ---
class StokerForecastSensor(StokerEntity, SensorEntity):
    """
    Sensor prognozy statycznej (obliczeniowej).
    Pozwala na symulację kosztów/zużycia na podstawie indeksów wydajności.
    """
    def __init__(self, coordinator, username, name, uid, efficiency_sid, target_temp_sid, 
                 is_fixed=False, force_index=False, force_slider=False, 
                 uid_for_slider=None, return_kg=False):
        super().__init__(coordinator, username)
        self._username = username
        self._uid = uid
        self._uid_for_slider = uid_for_slider or uid 
        
        # Generowanie ID encji (rozróżnienie KG vs PLN)
        suffix = "weight" if return_kg else "cost"
        self.entity_id = f"sensor.nbe_forecast_{uid.lower()}_{suffix}"
        
        self._attr_name = f"Prognoza - {name}"
        self._attr_unique_id = f"nbe_{username}_{uid}_forecast_{suffix}"
        self._return_kg = return_kg
        
        # Pamięć dla "ostatniej dobrej wartości" (debiasing)
        self._last_valid_forecast = 0.0
        self._last_valid_update = "Oczekiwanie na dane..."

        if self._return_kg:
            self._attr_native_unit_of_measurement = "kg"
            self._attr_device_class = SensorDeviceClass.WEIGHT
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:weight-kilogram"
        else:
            self._attr_native_unit_of_measurement = "PLN"
            self._attr_device_class = SensorDeviceClass.MONETARY
            self._attr_state_class = SensorStateClass.TOTAL
            self._attr_icon = "mdi:cash-clock" if force_index else "mdi:calculator-variant"

        self._efficiency_sid = efficiency_sid
        self._target_temp_sid = target_temp_sid
        self._is_fixed = is_fixed
        self._force_index = force_index
        self._force_slider = force_slider

    async def _update_manual_trigger(self, event):
        """Wymusza odświeżenie po zmianie parametrów wejściowych (np. zmiana ceny)."""
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Nasłuchiwanie zmian w encjach sterujących prognozą."""
        await super().async_added_to_hass()
        
        # Śledzimy cenę i temperaturę zadaną
        tracked_entities = [ENTITY_PELLET_PRICE, self._target_temp_sid]
        
        # Śledzimy suwak izolacji/wydajności
        slider_entity = f"number.nbe_insulation_factor_{self._uid_for_slider}"
        tracked_entities.append(slider_entity)
        
        # Jeśli to prognoza realna (nie symulacja), śledzimy indeks wyliczony przez inny sensor
        if (self._force_index or not self._force_slider) and self._efficiency_sid:
            tracked_entities.append(self._efficiency_sid)

        # Specyficzne encje dla modelu CWU
        if self._is_fixed:
            tracked_entities.extend([
                ENTITY_DHW_TANK_VOLUME, 
                SENSOR_DHW_TEMPERATURE
            ])
            
        for entity_id in tracked_entities:
            if entity_id:
                self.async_on_remove(
                    async_track_state_change_event(self.hass, entity_id, self._update_manual_trigger)
                )

    @property
    def extra_state_attributes(self):
        return {
            "last_valid_update": self._last_valid_update,
            "uid_slider_used": self._uid_for_slider,
            "calculation_mode": "Fixed/DHW" if self._is_fixed else ("Simulation" if self._force_slider else "Index-based")
        }

    @property
    def native_value(self):
        try:
            # 1. Pobranie ceny pelletu
            p_state = self.hass.states.get(ENTITY_PELLET_PRICE)
            # Domyślnie 1200 PLN / 1000 = 1.2 PLN/kg
            price_per_kg = float(p_state.state) / 1000 if p_state and p_state.state not in ["unknown", "unavailable"] else 1.2

            result_kg = 0.0

            # 2. Model CWU (Stały zład wody)
            if self._is_fixed:
                data = self.coordinator.data or {}
                dhw_sensor = float(data.get("frontdata", {}).get("dhw", 40.0))
                if dhw_sensor:
                    v_state = self.hass.states.get(ENTITY_DHW_TANK_VOLUME)
                    
                    volume = float(v_state.state) if v_state and v_state.state not in ["unknown", "unavailable"] else 200.0
                    
                    # Pobieramy atrybuty temperatury z sensora CWU
                    temp_target = float(data.get("frontdata", {}).get("dhwwanted", 50.0)) + 10
                    temp_actual = float(data.get("dhwdata", {}).get("8", 40.0))
                    
                    delta_temp_dhw = max(0, temp_target - temp_actual)
                    
                    # Obliczenie energii: (V * deltaT * ciepło_właściwe) / (wartość_opałowa * sprawność)
                    # 1.163 to Wh/kgK (zmienione na kWh w stałej)
                    energy_kwh = volume * delta_temp_dhw * SPECIFIC_HEAT_WATER_KWH
                    result_kg = energy_kwh / (PELLET_CALORIFIC_KWH * BOILER_EFFICIENCY_DHW)

            # 3. Model Budynków (Grzejniki/Podłogówka)
            else:
                eff_val = 0.6  # Fallback

                if self._force_slider:
                    # Tryb SYMULACJI (zawsze suwak)
                    ins_state = self.hass.states.get(f"number.nbe_insulation_factor_{self._uid_for_slider}")
                    if ins_state and ins_state.state not in ["unknown", "unavailable"]:
                        eff_val = float(ins_state.state)
                else:
                    # Tryb REALNY (najpierw indeks, potem suwak jako fallback)
                    eff_state = self.hass.states.get(self._efficiency_sid)
                    if eff_state and eff_state.state not in ["unknown", "unavailable", "0.0", "0"]:
                        eff_val = float(eff_state.state)
                    else:
                        ins_state = self.hass.states.get(f"number.nbe_insulation_factor_{self._uid_for_slider}")
                        if ins_state and ins_state.state not in ["unknown", "unavailable"]:
                            eff_val = float(ins_state.state)

                # Dane pogodowe z koordynatora
                wd = (self.coordinator.data or {}).get("weatherdata", {})
                try:
                    temp_ext = float(str(wd.get("1", 0)).replace(",", "."))
                except (ValueError, TypeError):
                    temp_ext = 0.0

                t_state = self.hass.states.get(self._target_temp_sid)
                t_dest = float(t_state.state) if t_state and t_state.state not in ["unknown", "unavailable"] else 22.0
                
                delta_t_bldg = max(0, t_dest - temp_ext)
                result_kg = eff_val * delta_t_bldg

            # 4. Przeliczenie na finalną jednostkę
            final_val = result_kg if self._return_kg else (result_kg * price_per_kg)

            # Walidacja wyniku i aktualizacja pamięci "Last Valid"
            if final_val > 0:
                self._last_valid_forecast = final_val
                self._last_valid_update = datetime.now().strftime("%H:%M:%S")
                return round(final_val, 2)
            
            # Zwróć ostatnią zapamiętaną wartość, jeśli nowa to 0 (np. podczas błędu danych pogodowych)
            if final_val <= 0 and self._last_valid_forecast > 0:
                return round(self._last_valid_forecast, 2)

            return round(final_val, 2)

        except Exception as e:
            _LOGGER.debug("Błąd obliczeń prognozy %s: %s", self._uid, e)
            return round(self._last_valid_forecast, 2)

# --- TOTAL COST SENSOR ---
class StokerCostTotalSensor(StokerEntity, SensorEntity, RestoreEntity):
    """
    Sensor akumulujący całkowity koszt (long-term statistics).
    Nalicza opłaty na podstawie przyrostu (delty) kilogramów i aktualnej ceny.
    """

    def __init__(self, coordinator, username, name, uid, consumption_sid):
        super().__init__(coordinator, username)
        self._username = username
        self.entity_id = f"sensor.nbe_{uid}_cost_total"
        self._attr_name = f"Koszt całkowity - {name}"
        self._attr_unique_id = f"nbe_{username}_{uid}_cost_total"
        self._attr_native_unit_of_measurement = "PLN"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:cash-register"
        
        self._consumption_sid = consumption_sid
        self._attr_native_value = 0.0
        self._last_known_kg_total = 0.0

    async def async_added_to_hass(self):
        """Przywrócenie stanu portfela i synchronizacja licznika przy starcie."""
        await super().async_added_to_hass()
        
        # 1. Przywróć ostatnią zapisaną kwotę z bazy danych HA
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in ["unknown", "unavailable"]:
            try:
                self._attr_native_value = float(last_state.state)
            except ValueError:
                self._attr_native_value = 0.0
        
        # 2. Pobierz aktualny stan licznika KG, aby wyznaczyć punkt zero dla przyrostów
        kg_state = self.hass.states.get(self._consumption_sid)
        if kg_state and kg_state.state not in ["unknown", "unavailable"]:
            try:
                self._last_known_kg_total = float(kg_state.state)
            except ValueError:
                self._last_known_kg_total = 0.0
        
        _LOGGER.info(
            "Zainicjalizowano licznik kosztów %s: %s PLN. Punkt startowy: %s kg",
            self._attr_name, self._attr_native_value, self._last_known_kg_total
        )

    def _handle_coordinator_update(self) -> None:
        """Obliczanie przyrostu kosztu przy każdej aktualizacji koordynatora."""
        kg_state = self.hass.states.get(self._consumption_sid)
        p_state = self.hass.states.get(ENTITY_PELLET_PRICE)

        if not kg_state or kg_state.state in ["unknown", "unavailable"]:
            return

        try:
            current_kg_total = float(kg_state.state)
            
            # Pobranie ceny pelletu z suwaka zdefiniowanego w const.py
            # Fallback na 1.2 PLN/kg (1200 za tonę)
            price_per_kg = 1.2
            if p_state and p_state.state not in ["unknown", "unavailable"]:
                price_per_kg = float(p_state.state) / 1000

            # Obliczamy deltę (ile przybyło od ostatniego pomiaru)
            if current_kg_total > self._last_known_kg_total:
                kg_delta = current_kg_total - self._last_known_kg_total
                cost_increment = kg_delta * price_per_kg
                
                # Dodajemy do istniejącej sumy
                self._attr_native_value = round((self._attr_native_value or 0.0) + cost_increment, 2)
                self._last_known_kg_total = current_kg_total
                
                _LOGGER.debug(
                    "Przyrost kosztu %s: +%s PLN (delta %s kg)",
                    self._attr_name, round(cost_increment, 2), round(kg_delta, 3)
                )
            
            # Obsługa resetu źródłowego licznika KG (np. reset licznika dobowego o północy)
            elif current_kg_total < self._last_known_kg_total:
                # Synchronizujemy licznik bez doliczania kosztów (ważne przy sensorach typu 'daily')
                self._last_known_kg_total = current_kg_total

            # Zapisujemy stan w HA
            self.async_write_ha_state()

        except ValueError as e:
            _LOGGER.error("Błąd przetwarzania liczb w sensorze kosztu %s: %s", self.entity_id, e)


# --- ACTUAL HEATING COST SENSOR ---
class StokerHeatingCostActualSensor(StokerEntity, SensorEntity):
    """Sensor wyliczający koszt aktualnego zużycia dobowego (chwilowy)."""
    
    def __init__(self, coordinator, username):
        super().__init__(coordinator, username)
        self._username = username
        self.entity_id = "sensor.nbe_heating_cost_actual"
        self._attr_has_entity_name = True
        self._attr_name = "Koszt aktualny (Dziś)"
        self._attr_unique_id = f"nbe_{username}_cost_actual"
        self._attr_native_unit_of_measurement = "PLN"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_icon = "mdi:cash-check"

    @property
    def native_value(self):
        try:
            # Pobieramy kg z dzisiaj bezpośrednio z koordynatora
            daily_kg = float(self.coordinator.data.get("stats", {}).get("day", 0.0))
            
            # Pobieramy cenę z Twojej stałej ENTITY_PELLET_PRICE
            price_state = self.hass.states.get(ENTITY_PELLET_PRICE)
            # Fallback 1250 PLN/t
            price_ton = float(price_state.state) if price_state and price_state.state not in ["unknown", "unavailable"] else 1250.0
            
            # (kg / 1000) * cena_za_tone
            return round((daily_kg / 1000.0) * price_ton, 2)
        except Exception as e:
            _LOGGER.debug("Błąd obliczeń kosztu dobowego: %s", e)
            return 0.0


# --- HOUSE & OFFICE CONSUMPTION SENSOR ---
class StokerDividedConsumptionSensor(StokerEntity, SensorEntity, RestoreEntity):
    """Uniwersalny sensor rozdzielający zużycie między Dom a Biuro."""
    
    def __init__(self, coordinator, username, is_house=True):
        super().__init__(coordinator, username)
        self._username = username
        self._is_house = is_house
        
        suffix = "house" if is_house else "office"
        self.entity_id = f"sensor.nbe_{suffix}_consumption_total"
        self._attr_name = "Dom - Konsumpcja całkowita" if is_house else "Biuro - Konsumpcja całkowita"
        self._attr_unique_id = f"nbe_{username}_{suffix}_consumption_total"
        self._attr_icon = "mdi:home-lightning-bolt" if is_house else "mdi:office-building-marker"
        self._attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_device_class = SensorDeviceClass.WEIGHT
        
        self._attr_native_value = 0.0
        self._last_day_stat = None 
        self._last_update_time = None
        self._house_baseline_kgh = 0.0
        self._last_increment = 0.0

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) and last_state.state not in ("unknown", "unavailable"):
            try:
                self._attr_native_value = float(last_state.state)
            except ValueError:
                self._attr_native_value = 0.0
        
        if self.coordinator.data and "stats" in self.coordinator.data:
            val = self.coordinator.data["stats"].get("day")
            if val is not None:
                self._last_day_stat = float(val)
                self._last_update_time = time.time()

    def _calculate_house_baseline(self, data):
        eff_state = self.hass.states.get(SENSOR_HOUSE_EFFICIENCY)
        try:
            idx = float(eff_state.state) if eff_state and eff_state.state not in ("unknown", "unavailable") else 0.8
        except: idx = 0.8

        t_state = self.hass.states.get(ENTITY_TEMP_TARGET_HOUSE)
        try:
            t_target = float(t_state.state) if t_state and t_state.state not in ("unknown", "unavailable") else 22.0
        except: t_target = 22.0
        
        try:
            temp_ext = float(str(data.get("weatherdata", {}).get("1", 0)).replace(",", "."))
        except: temp_ext = 0.0

        return (idx * max(0.1, t_target - temp_ext)) / 24.0

    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if not data or "stats" not in data:
            return

        try:
            current_day_stat = float(data["stats"].get("day", 0.0))
        except (ValueError, TypeError):
            return

        # 1. OBSŁUGA RESETU O PÓŁNOCY (Z Twojej starej klasy)
        if current_day_stat < self._last_day_stat:
            _LOGGER.debug("Wykryto reset licznika dobowego o północy.")
            self._last_day_stat = current_day_stat
            self._last_update_time = time.time()
            self._last_increment = 0.0
            return  # KLUCZOWE: Wychodzimy, żeby nie naliczyć błędu

        # 2. Obliczanie delty
        total_delta = current_day_stat - self._last_day_stat
        
        # Jeśli brak przyrostu, aktualizujemy tylko czas i wychodzimy
        if total_delta <= 0:
            self._last_update_time = time.time()
            return

        now_ts = time.time()
        time_diff_hours = (now_ts - self._last_update_time) / 3600.0
        
        # Zabezpieczenie przed skokami czasu (max 1h)
        if time_diff_hours > 1.0 or time_diff_hours < 0:
            time_diff_hours = 0.0 

        # Aktualizacja zmiennych bazowych
        self._last_day_stat = current_day_stat
        self._last_update_time = now_ts

        # 3. Oblicz Baseline Domu
        self._house_baseline_kgh = self._calculate_house_baseline(data)
        expected_house_kg = self._house_baseline_kgh * time_diff_hours

        # 4. Sprawdzenie statusów urządzeń
        pump_house = self.hass.states.get(ENTITY_PUMP_HOUSE)
        pump_office = self.hass.states.get(ENTITY_PUMP_OFFICE)
        switch_office = self.hass.states.get(ENTITY_SWITCH_OFFICE)
        boiler = self.hass.states.get(ENTITY_BOILER_STATUS)

        is_house_on = (pump_house and pump_house.state == "on")
        is_office_active = (is_house_on and pump_office and pump_office.state == "on" and switch_office and switch_office.state == "on")
        is_cwu = (boiler and boiler.state in ["CWU", "state_7"])

        # 5. LOGIKA PODZIAŁU (Z zachowaniem braku luki)
        increment = 0.0
        TOLERANCE = 1.15

        if is_cwu:
            increment = 0.0
        elif self._is_house:
            if not is_house_on:
                increment = 0.0
            elif is_office_active:
                # Dom bierze swoją część z marginesem
                increment = min(total_delta, expected_house_kg * TOLERANCE)
            else:
                # Tylko dom grzeje
                increment = total_delta
        else: # Biuro
            if is_office_active:
                # Biuro bierze całą resztę (Gwarancja sumy)
                house_share = min(total_delta, expected_house_kg * TOLERANCE)
                increment = max(0.0, total_delta - house_share)
            else:
                increment = 0.0

        # 6. ZAPIS STANU
        self._last_increment = increment
        if increment > 0:
            current_val = self._attr_native_value if self._attr_native_value is not None else 0.0
            self._attr_native_value = round(current_val + increment, 4)
            self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        return {
            "baseline_kgh": round(self._house_baseline_kgh, 3),
            "last_increment_kg": round(self._last_increment, 4)
        }


# --- PELLETS LEFT FOR DAYS SENSOR ---
class StokerRangeSensor(StokerEntity, SensorEntity):
    """
    Sensor zasięgu. 
    Łączy aktualny stan zasobnika z dynamicznym modelem zapotrzebowania (Burn Rate).
    """
    def __init__(self, coordinator, username):
        super().__init__(coordinator, username)
        self._username = username
        self.entity_id = "sensor.nbe_pellet_range"
        self._attr_name = "Zasobnik - Zasięg"
        self._attr_unique_id = f"nbe_{username}_range_days"
        self._attr_native_unit_of_measurement = "dni"
        self._attr_icon = "mdi:calendar-clock"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Oblicza zasięg: 70% Realne spalanie (wczoraj) + 30% Prognoza."""
        try:
            data = self.coordinator.data or {}
            current_pellet_kg = float(self._get_api_data("frontdata.hoppercontent", 0.0))

            # 1. Pobieramy spalanie z wczoraj (fakt)
            yesterday_burn = float(self._get_api_data("stats.yesterday", 0.0))

            # 2. Pobieramy prognozę (teoria)
            forecast_rate = self._get_value_safely(SENSOR_FORECAST_TOTAL_WEIGHT, 0.0)

            # 3. Model hybrydowy z przewagą faktów (70/30)
            if yesterday_burn > 0 and forecast_rate > 0:
                daily_burn_rate = (yesterday_burn * 0.7) + (forecast_rate * 0.3)
            elif yesterday_burn > 0:
                daily_burn_rate = yesterday_burn
            else:
                daily_burn_rate = forecast_rate

            # Zabezpieczenie przed dzieleniem przez zero
            if daily_burn_rate < 0.5:
                return 99.0

            days_remaining = current_pellet_kg / daily_burn_rate
            
            # Przechowujemy dane do atrybutów
            self._calculated_burn_rate = round(daily_burn_rate, 2)
            self._yesterday_weight = yesterday_burn
            self._forecast_weight = forecast_rate

            return round(days_remaining, 1)

        except Exception as e:
            _LOGGER.error("Błąd obliczania zasięgu hybrydowego: %s", e)
            return None

    @property
    def extra_state_attributes(self):
        """Atrybuty pokazujące wagę składowych modelu."""
        val = self.native_value
        attrs = {
            "model_weight_real": "70%",
            "model_weight_forecast": "30%",
            "status": "Stabilny"
        }
        
        if hasattr(self, '_calculated_burn_rate'):
            attrs["avg_daily_burn_calculated"] = f"{self._calculated_burn_rate} kg/d"
            attrs["yesterday_actual"] = f"{self._yesterday_weight} kg"
            attrs["forecast_theoretical"] = f"{self._forecast_weight} kg"

        if val and val != 99.0:
            finish_date = dt_util.now() + timedelta(days=val)
            attrs["expected_empty_date"] = finish_date.strftime("%Y-%m-%d %H:%M")
            if val < 2:
                attrs["status"] = "Uzupełnić pellet w zasobniku"
        
        return attrs

# --- DHW TOTAL CONSUMPTION SENSOR ---
class StokerDHWConsumptionTotalSensor(StokerEntity, SensorEntity, RestoreEntity):
    """
    Sensor kumulatywny zużycia pelletu na CWU.
    Działa jako licznik długoterminowy, odporny na reszty dobowe sterownika.
    """
    def __init__(self, coordinator, username):
        super().__init__(coordinator, username)
        self.entity_id = "sensor.nbe_dhw_consumption_total"
        self._attr_unique_id = f"nbe_{username}_dhw_consumption_total"
        self._attr_name = "CWU - Konsumpcja całkowita"
        
        self._attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
        self._attr_device_class = SensorDeviceClass.WEIGHT
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:water-boiler"
        
        self._attr_native_value = 0.0
        self._last_dhw_stat = 0.0

    async def async_added_to_hass(self):
        """Przywracanie stanu licznika po restarcie HA."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        
        if last_state is not None and last_state.state not in ["unknown", "unavailable"]:
            try:
                self._attr_native_value = float(last_state.state)
            except ValueError:
                self._attr_native_value = 0.0
        
        # Inicjalizacja punktu odniesienia z koordynatora
        data = self.coordinator.data
        if data and "stats" in data:
            self._last_dhw_stat = float(data["stats"].get("dhw_day", 0.0))
        
        self.async_write_ha_state()

    def _handle_coordinator_update(self) -> None:
        """Obliczanie przyrostów na podstawie statystyk dobowych CWU."""
        data = self.coordinator.data
        if not data or "stats" not in data:
            return

        # Pobieramy dzisiejsze spalanie na CWU podawane przez sterownik
        current_dhw_stat = float(data["stats"].get("dhw_day", 0.0))
        
        # Logika obsługi przyrostu i resetu o północy
        if current_dhw_stat < self._last_dhw_stat:
            # Nastąpił reset dobowy - cały obecny stan to nasz nowy przyrost
            delta_dhw = current_dhw_stat
        else:
            # Standardowy przyrost w ciągu dnia
            delta_dhw = current_dhw_stat - self._last_dhw_stat
        
        # Aktualizacja punktu odniesienia
        self._last_dhw_stat = current_dhw_stat
        
        # Jeśli kocioł faktycznie coś spalił na wodę, dodajemy do licznika głównego
        if delta_dhw > 0:
            self._attr_native_value = round((self._attr_native_value or 0.0) + delta_dhw, 4)
            # Wymuszamy zapis stanu
            self.async_write_ha_state()


# --- OUTPUTS SENSOR ---
class StokerOutputSensor(StokerEntity, SensorEntity):
    """Sensor monitorujący konkretne wyjścia sterownika (np. % mocy wentylatora)."""
    
    def __init__(self, coordinator, username, output_id, name, icon, unit=None):
        super().__init__(coordinator, username)
        # Dynamiczne tworzenie entity_id na podstawie ID wyjścia
        safe_id = output_id.lower().replace('-', '_')
        self.entity_id = f"sensor.nbe_output_{safe_id}"
        self._output_id = output_id
        
        self._attr_name = name
        self._attr_unique_id = f"nbe_{username}_out_{output_id}"
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        """Pobiera wartość wyjścia i czyści ją ze zbędnych znaków."""
        raw_val = self.coordinator.data.get("leftoutput", {}).get(self._output_id, {}).get("val", "0")
        # Usuwamy % i spacje, aby HA mógł to traktować jako liczbę jeśli to możliwe
        return str(raw_val).replace("%", "").strip()

# --- SETTINGS SENSORS ---
class StokerGroupedSettingsSensor(StokerEntity, SensorEntity):
    """
    Sensor zbierający ustawienia z danego menu w atrybuty.
    Native value to liczba ustawień w danej grupie.
    """
    
    def __init__(self, coordinator, username, name, menu_key, icon):
        super().__init__(coordinator, username)
        self.entity_id = f"sensor.nbe_settings_{menu_key}"
        self._menu_key = menu_key
        
        self._attr_name = name
        self._attr_unique_id = f"nbe_{username}_settings_{menu_key}"
        self._attr_icon = icon

    @property
    def native_value(self):
        """Zwraca liczbę pozycji w danym menu."""
        menu_data = self.coordinator.data.get("menus", {}).get(self._menu_key, {})
        return len(menu_data) if menu_data else 0
    
    @property
    def extra_state_attributes(self):
        """Wrzuca wszystkie klucze i wartości z menu do atrybutów sensora."""
        menu_data = self.coordinator.data.get("menus", {}).get(self._menu_key, {})
        if not menu_data:
            return {}
        
        # Tworzy słownik { 'Nazwa Ustawienia': 'Wartość' }
        return {
            v.get("text", k): v.get("val") 
            for k, v in menu_data.items() 
            if isinstance(v, dict)
        }


# --- DIAGNOSTIC SENSOR ---
class StokerDiagnosticDump(StokerEntity, SensorEntity):
    """
    Sensor diagnostyczny przechowujący surowe dane JSON z koordynatora.
    Domyślnie wyłączony, aby nie obciążać bazy danych HA.
    """
    def __init__(self, coordinator, username):
        super().__init__(coordinator, username)
        self._attr_name = "Diagnostyka RAW"
        self.entity_id = "sensor.nbe_diagnostic_raw"
        self._attr_unique_id = f"nbe_{username}_diagnostic_raw"
        
        # Przypisanie do kategorii diagnostycznej (ikona klucza w interfejsie)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        # Sensor jest ukryty przy pierwszym uruchomieniu - trzeba go włączyć ręcznie
        self._attr_entity_registry_enabled_default = False
        self._attr_icon = "mdi:database-import"

    @property
    def native_value(self):
        """Status ogólny komunikacji."""
        if self.coordinator.data:
            return "Połączono"
        return "Brak danych"

    @property
    def extra_state_attributes(self):
        """Mapuje surowe słowniki danych do atrybutów sensora."""
        data = self.coordinator.data or {}
        flat_data = {}
        
        # Wybieramy kluczowe sekcje do dumpu
        keys_to_dump = [
            "weatherdata", "boilerdata", "hopperdata", "dhwdata", "infomessages", 
            "frontdata", "miscdata", "leftoutput", "rightoutput", "stats"
        ]
        
        for key in keys_to_dump:
            if key in data and data[key] is not None:
                flat_data[key] = data[key]
        
        return flat_data


# --- SETUP ---
async def async_setup_entry(hass, entry, async_add_entities):
    """Główna konfiguracja sensorów NBE w Home Assistant."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    username = coordinator.client.username.lower()

    # --- FAZA 1: SENSORY PODSTAWOWE (Dane bezpośrednie z koordynatora) ---
    entities = [StokerSensor(coordinator, username, *cfg) for cfg in SENSOR_MAP]

    entities.extend([
        # Techniczne i diagnostyczne
        StokerDiagnosticDump(coordinator, username),
        
        # Statystyki i CWU
        StokerDHWConsumptionTotalSensor(coordinator, username),
        StokerDHWEfficiencySensor(coordinator, username),
        
        # Sensory wydzielonego zużycia (Logika rozdzielania Dom/Biuro)
        StokerDividedConsumptionSensor(coordinator, username, is_house=True),
        StokerDividedConsumptionSensor(coordinator, username, is_house=False),
    ])

    # --- KONFIGURACJA WYJŚĆ (Outputs) ---
    for out_id, out_name, out_icon, out_unit in STOKER_OUTPUTS_CONFIG:
        entities.append(StokerOutputSensor(coordinator, username, out_id, out_name, out_icon, out_unit))

    # --- KONFIGURACJA GRUPOWYCH USTAWIEŃ (Menus) ---
    for name, menu_key, icon in STOKER_SETTINGS_MENU_CONFIG:
        entities.append(StokerGroupedSettingsSensor(coordinator, username, name, menu_key, icon))

    # Dodanie pierwszej fali sensorów
    async_add_entities(entities)

    # --- FAZA 2: SENSORY OBLICZENIOWE (Koszty, Prognozy, Zasięg) ---
    try:
        computed_entities = [
            # 1. Koszty rzeczywiste (PLN) bazujące na Twoich sensorach "Total"
            StokerCostTotalSensor(coordinator, username, "Dom", "house", "sensor.nbe_house_consumption_total"),
            StokerCostTotalSensor(coordinator, username, "Biuro", "office", "sensor.nbe_office_consumption_total"),
            StokerCostTotalSensor(coordinator, username, "CWU", "dhw", "sensor.nbe_dhw_consumption_total"),
            StokerHeatingCostActualSensor(coordinator, username),

            # 2. Indeksy efektywności i odchylenia
            StokerEfficiencySensor(coordinator, username, "Dom", "house", "sensor.nbe_consumption_statistics", "number.nbe_house_targer_temp", "month", use_wind=True),
            StokerEfficiencySensor(coordinator, username, "Biuro", "office", "sensor.nbe_consumption_statistics", "number.nbe_office_target_temp", "month", use_wind=True),
            StokerEfficiencyDeviationSensor(coordinator, username),

            # 3. Symulatory (PLN)
            StokerForecastSensor(coordinator, username, "Dom (Symulacja)", "house_sim", None, "number.nbe_house_target_temp", force_slider=True, uid_for_slider="house"),
            StokerForecastSensor(coordinator, username, "Biuro (Symulacja)", "office_sim", None, "number.nbe_office_target_temp", force_slider=True, uid_for_slider="office"),

            # 4. Zasięg zasobnika
            StokerRangeSensor(coordinator, username),
        ]
        
        # 5. Dynamiczne generowanie ujednoliconych prognoz (Waga i Koszt)
        targets = ["total", "house", "office", "dhw"]                                                                                                                   
        types = ["weight", "cost"]                                                                                                                                      
                                                                                                                                                                        
        for t in targets:                                                                                                                                               
            for tp in types:                                                                                                                                            
                computed_entities.append(StokerUnifiedForecastSensor(coordinator, username, target=t, forecast_type=tp))                                             

        async_add_entities(computed_entities)
        _LOGGER.info("Pomyślnie dodano sensory obliczeniowe Fazy 2")

    except Exception as e:
        _LOGGER.error("Błąd podczas inicjalizacji sensorów Fazy 2: %s", e)
