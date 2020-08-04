import os
import sys
import logging
from omnik.ha_logger import hybridlogger
import requests
import json
from .daylight import daylight
import threading
import time
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone

from .plugin_output import Plugin
from .plugin_client import Client
from .dsmr import DSRM
from copy import deepcopy
from cachetools import Cache

import importlib

# from .plugin_localproxy import LocalProxyPlugin

logger = logging.getLogger(__name__)


class DataLogger(object):

    def __init__(self, config, hass_api=None):
        # Defaults to UTC now() - every interval
        self.plant_update = {}
        self.hass_api = hass_api
        self.logger = logger
        self.config = config
        self.cache = Cache(maxsize=10)
        self.start_total_energy = {}
        self.pasttime = datetime.combine(date.today(), datetime.min.time()).timestamp()
        self.dsmr_access = threading.Condition(threading.Lock())

        if self.config.get('default', 'debug', fallback=False):
            logger.setLevel(logging.DEBUG)

        if not self._init_data_fields():
            sys.exit(1)
        # init energy cache
        # total_energy_cache.json
        self.persistant_cache_file = self.config.get('default', 'persistant_cache_file', fallback='./persistant_cache.json')
        self._load_persistant_cache()
        # read data_fields
        try:
            with open(self.data_config_file) as json_file_config:
                self.config.data_field_config = json.load(json_file_config)
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",
                                f"Error reading configuration file (data_fields.json). Exiting!. Error: {e.args}")
            raise e
            sys.exit(1)

        # read attributes
        if not self._read_attributes():
            sys.exit(1)

        self.every = self._get_interval()
        self.interval_aggregated = self._get_interval_aggregated()

        # Make sure we check for a recent update first
        self.last_update_time = datetime.now(timezone.utc) - timedelta(seconds=self.interval_aggregated)

        # Initialize plugin paths
        sys.path.append(self.__expand_path('plugin_output'))
        sys.path.append(self.__expand_path('plugin_client'))
        sys.path.append(self.__expand_path('plugin_localproxy'))

        self.city = self.config.get('default', 'city', fallback='Amsterdam')
        try:
            self.dl = daylight(self.city)
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", f"City '{self.city}' not recognized. Error: {e}")
            sys.exit(1)

        # Initialize client
        self._init_client()
        # Initialize output plugins
        self._init_output_plugins()

        self.omnik_api_level = 0

        # Init dsmr
        self._init_dsmr()

    def _init_data_fields(self):
        self.config.data_config_file_args = self.config.get('default', 'data_config', fallback='')
        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                            f"Data configuration [args]: '{self.config.data_config_file_args}'.")
        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                            f"Data configuration [path]: '{self.config.data_config_file_path}'.")
        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                            f"Data configuration [shared]: '{self.config.data_config_file_shared}'.")
        if self.config.configfile:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO", f"Using configuration from '{self.config.configfile}'.")

        if os.path.exists(self.config.data_config_file_args):
            self.data_config_file = self.config.data_config_file_args
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO",
                                f"Using configured data configuration from '{self.data_config_file}'.")
        elif os.path.exists(self.config.data_config_file_path):
            self.data_config_file = self.config.data_config_file_path
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO",
                                f"Using configured data configuration from '{self.data_config_file}'.")
        elif os.path.exists(self.config.data_config_file_shared):
            self.data_config_file = self.config.data_config_file_shared
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO",
                                f"Using shared data configuration from '{self.data_config_file}'.")
        else:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",
                                "No valid data configuration file (data_fields.json) found. Exiting!")
            return False
        return True

    def _init_attribute_dict(self):
        self.config.attributes = {}
        asset_classes = list(['omnik', 'omnik_dsmr', 'dsmr', 'dsmr_gas'])
        self.config.attributes['asset'] = {
            'omnik': list(['inverter', 'plant_id', 'last_update']),
            'omnik_dsmr': list(['inverter', 'plant_id', 'EQUIPMENT_IDENTIFIER', 'last_update']),
            'dsmr': list(['EQUIPMENT_IDENTIFIER', 'timestamp']),
            'dsmr_gas': list(['EQUIPMENT_IDENTIFIER_GAS', 'timestamp_gas'])
            }
        self.config.attributes['model'] = {
            'omnik': 'Omniksol',
            'omnik_dsmr': 'Omnik data logger',
            'dsmr': 'DSMR electicity meter',
            'dsmr_gas': 'DSMR gas meter'
            }
        self.config.attributes['mf'] = {
            'omnik': 'Omnik',
            'omnik_dsmr': 'JBsoft',
            'dsmr': 'Netbeheer Nederland',
            'dsmr_gas': 'Netbeheer Nederland'
            }
        self.config.attributes['identifier'] = {
            'omnik': 'plant_id',
            'omnik_dsmr': 'plant_id',
            'dsmr': 'EQUIPMENT_IDENTIFIER',
            'dsmr_gas': 'EQUIPMENT_IDENTIFIER_GAS'
            }
        self.config.attributes['devicename'] = {
            'omnik': 'Inverter',
            'omnik_dsmr': 'Omnik_data_logger',
            'dsmr': 'DSMR_electicity_meter',
            'dsmr_gas': 'DSMR_gasmeter'
            }
        return asset_classes

    def _init_attribute_set(self, attribute, asset_class, type='string'):
        if attribute not in self.config.attributes:
            self.config.attributes[attribute] = {}
        if not self.config.has_option('attributes', f'{attribute}.{asset_class}'):
            return
        if type == 'list':
            self.config.attributes[attribute][asset_class] = self.config.getlist(
                'attributes', f'asset.{asset_class}')
        else:
            self.config.attributes[attribute][asset_class] = self.config.get('attributes', f'{attribute}.{asset_class}')

    def _read_attributes(self):
        asset_classes = self._init_attribute_dict()
        try:
            if self.config.has_option('attributes', 'asset_classes'):
                asset_classes += list(set(self.config.getlist('attributes', 'asset_classes')) - set(asset_classes))
            for asset_class in asset_classes:
                self._init_attribute_set('asset', asset_class, 'list')
                self._init_attribute_set('model', asset_class)
                self._init_attribute_set('mf', asset_class)
                self._init_attribute_set('identifier', asset_class)
                self._init_attribute_set('devicename', asset_class)
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",
                                f"Error reading attributes from config. Error: {e.args}")
            raise e
            return False
        return True

    def terminate(self):
        # Cleanup Client
        self._terminate_client()
        # Cleanup Output plugins
        self._terminate_output_plugins()
        # Terminate DSMR
        if self.dsmr:
            self.dsmr.terminate()

    def _init_client(self):
        # For now the default client is not set by default, client should be configured in the config
        # options are: localproxy, solarmanpv and omnikportal
        self.client_module = self.config.get('plugins', 'client', None)
        if not self.client_module:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "ERROR", "No 'client' parameter configured under the [plugin] section.")
            sys.exit(1)

        hybridlogger.ha_log(self.logger, self.hass_api, "INFO", f"Initializing client : {self.client_module}.")
        # Try to load client
        try:
            Client.logger = self.logger
            Client.config = self.config
            Client.hass_api = self.hass_api
            # __import__(self.client_module)
            spec = importlib.util.find_spec(self.client_module)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.client = Client.client[0]
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "ERROR", f"Client '{self.client_module}' could not be initialized. Error: {e}")
            sys.exit(1)

    def _terminate_client(self):
        while Client.client:
            Client.client.pop(0).terminate()

    def _init_output_plugins(self):
        self.plugins = self.config.getlist('plugins', 'output', fallback=[''])
        if self.plugins and self.plugins[0]:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO", f"Plugins enabled: {self.plugins}.")
        else:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "WARNING", "No output plugins configured! Monitoring only.")
        # Import output plugins
        if self.plugins and self.plugins[0]:
            Plugin.logger = self.logger
            Plugin.config = self.config
            Plugin.hass_api = self.hass_api

            for plugin in self.plugins:
                spec = importlib.util.find_spec(plugin)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # importlib.import_module(plugin)

    def _terminate_output_plugins(self):
        while Plugin.plugins:
            Plugin.plugins.pop(0).terminate()

    def _init_dsmr(self):
        terminals = self.config.getlist('dsmr', 'terminals', fallback=[])
        if terminals and terminals[0]:
            self.dsmr = DSRM()
            self.dsmr.config = self.config
            self.dsmr.logger = self.logger
            self.dsmr.hass_api = self.hass_api
            self.dsmr.datalogger = self
            self.dsmr.initialize(terminals=terminals, dsmr_callback=self.dsmr_callback)
        else:
            self.dsmr = None
        self.dsmr_data = {}

    def _get_dsmr_data(self, plant, data):
        # if dsmr measurements are not enabled then return
        if not self.dsmr:
            return
        # Try to merge with the latest dsmr data available
        complete = False
        tries = 20
        while tries > 0:
            self.dsmr_access.acquire()
            if plant in self.dsmr_data:
                # Insert raw DSMR data
                data.update(self._dsmr_cache(plant, data['last_update']))
                # Insert calculated netto values (solar - net)
                self._calculate_consumption(data)
                complete = True
            self.dsmr_access.release()
            tries -= 1
            if not complete:
                time.sleep(1)
            else:
                break
        if not tries:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "WARNING", f"Could not combine DSMR data for plant {plant}. "
                                "Did you configure plant_id at your dsmr terminal config?")

    def _calculate_consumption(self, data):
        # Calculate cumulative energy direct used
        data['energy_direct_use'] = data['total_energy_recalc'] - data['total_energy_offset'] - data['energy_delivered_net']
        data['energy_used'] = data['energy_used_net'] + data['energy_direct_use']  # use as v3 * 1000 for pvoutput
        # Calculate the actual power used
        if 'current_power' in data:
            data['power_direct_use'] = data['current_power'] - (data['CURRENT_ELECTRICITY_DELIVERY'] * Decimal('1000'))
            # Should not be negative, but timestamps can be out of sync.
            if data['power_direct_use'] < Decimal('0'):
                data['power_direct_use'] = Decimal('0')
            data['power_consumption'] = data['CURRENT_ELECTRICITY_USAGE'] * Decimal('1000') + data['power_direct_use']
        else:
            data['power_consumption'] = data['CURRENT_ELECTRICITY_USAGE'] * Decimal('1000')
        data['last_update_calc'] = time.time()

    def dsmr_callback(self, terminal, dsmr_message):
        # print(f"{dsmr_message['gas_consumption_totall']} =
        # m3 {dsmr_message['gas_consumption_hour']} m3/h - {dsmr_message['timestamp_gas']}")
        if dsmr_message['plant_id']:
            plant_id = dsmr_message.pop('plant_id')
            # Get last total energy form cache (if available) and ad to the dataset
            # dsmr_message['total_energy_cache'] = self.total_energy(plant_id)
            self.dsmr_access.acquire()
            self._dsmr_cache_update(plant_id, dsmr_message)
            # self.dsmr_data[plant_id] = deepcopy(dsmr_message)
            self.dsmr_access.release()
            if plant_id in self.plant_update:
                self._proces_pushed_net_event(plant_id, dsmr_message)
        else:
            self._proces_pushed_net_event(None, dsmr_message)

    def _dsmr_cache_update(self, plant_id, dsmr_message):
        if plant_id not in self.dsmr_data:
            self.dsmr_data[plant_id] = list()
        if len(self.dsmr_data[plant_id]) == 10:
            self.dsmr_data[plant_id].pop(0)
        self.dsmr_data[plant_id].append(dsmr_message)

    def _dsmr_cache(self, plant_id, timestamp):
        max_delta = -1
        best_data = None
        for data in reversed(self.dsmr_data[plant_id]):
            dsmr_ts = data['timestamp']
            delta = abs(timestamp - dsmr_ts)
            if delta < max_delta or max_delta < 0:
                max_delta = delta
                best_data = data
        return best_data

    def _get_interval(self):
        if self.config.has_option('default', 'interval'):
            return int(self.config.get('default', 'interval'))
        else:
            return 0

    def _get_interval_aggregated(self):
        if self.config.has_option('default', 'interval_aggregated'):
            return int(self.config.get('default', 'interval_aggregated'))
        else:
            return 300

    def _validate_user_login(self):
        self.omnik_api_level = 0
        try:
            self.client.initialize()
            # Logged on
            self.omnik_api_level = 1
        except requests.exceptions.RequestException as err:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "WARNING", f"Request error during account validation omnik portal: {err}")
        except requests.exceptions.HTTPError as errh:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "WARNING", f"HTTP error during account validation omnik portal: {errh}")
        except requests.exceptions.ConnectionError as errc:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "WARNING", f"Connection error during account validation omnik portal: {errc}")
        except requests.exceptions.Timeout as errt:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "WARNING", f"Timeout error during account validation omnik portal: {errt}")
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", e)

    def _logon(self):
        # Log on to the omnik portal to enable fetching plant's
        if (self.omnik_api_level == 0):
            self._validate_user_login()
            if (self.omnik_api_level == 0):
                return False
        return True

    def _fetch_plants(self):
        # Fetch te plant's available for the account
        if (not self.plant_update or self.omnik_api_level == 1):
            try:
                plants = self.client.getPlants()
                for pid in plants:
                    self.plant_update[str(pid['plant_id'])] = self.last_update_time
                self.omnik_api_level = 2
            except requests.exceptions.RequestException as err:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", f"Request error: {err}")
                self.omnik_api_level = 0
                return False
            except requests.exceptions.HTTPError as errh:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", f"HTTP error: {errh}")
                self.omnik_api_level = 0
                return False
            except requests.exceptions.ConnectionError as errc:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", f"Connection error: {errc}")
                self.omnik_api_level = 0
                return False
            except requests.exceptions.Timeout as errt:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", f"Timeout error: {errt}")
                self.omnik_api_level = 0
                return False
            except Exception as e:
                hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", e)
                self.omnik_api_level = 0
                return False
        return True

    def _listen_for_update(self):
        data = self.client.getPlantData()
        return data

    def _process_received_update(self, data, netdata=False, plant=None):
        # Get the report time
        newreporttime = datetime.fromtimestamp(data['last_update']).astimezone(timezone.utc)
        if not plant:
            plant = data['plant_id']
        if netdata:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO",
                                f"Net data update for plant '{plant}' update at UTC {newreporttime}")
        else:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO",
                                f"Update for plant {plant} update at UTC {newreporttime}")

        return plant

    def _sundown_reset_power(self, data):
        if self.client.use_timer:
            if self.sundown:
                data['current_power'] = Decimal('0')

    def _fetch_update(self, plant):
        try:
            data = self.client.getPlantData(plant)
            if data:
                self._sundown_reset_power(data)
                # Get the actual report time from the omnik portal
                newreporttime = datetime.fromtimestamp(data['last_update']).astimezone(timezone.utc)
                # Only proces updates that occured after we started or start a single measurement (TODO)
                if (newreporttime > self.plant_update[plant] or not self.every or self.sundown):
                    hybridlogger.ha_log(self.logger, self.hass_api, "INFO",
                                        f"Update for plant {plant} update at UTC {newreporttime}")
                    # the newest plant_update time will be used as a baseline to program the timer
                    self.last_update_time = newreporttime
                    # Store the plant_update time for each indiviual plant,
                    # update only if there is a new report available to avoid duplicates
                    self.plant_update[plant] = newreporttime
                    data['plant_id'] = plant
                    return data
                else:
                    hybridlogger.ha_log(self.logger, self.hass_api, "INFO",
                                        f'No recent report update to process. Last report at UTC {newreporttime}')
                    return None

        except requests.exceptions.RequestException as err:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", f"Request error: {err}")
            self.omnik_api_level = 0
            # Abort retry later
            return None
        except requests.exceptions.HTTPError as errh:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", f"HTTP error: {errh}")
            self.omnik_api_level = 0
            # Abort retry later
            return None
        except requests.exceptions.ConnectionError as errc:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", f"Connection error: {errc}")
            self.omnik_api_level = 0
            # Abort retry later
            return None
        except requests.exceptions.Timeout as errt:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", f"Timeout error: {errt}")
            self.omnik_api_level = 0
            # Abort retry later
            return None
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", f"Unexpected error during data handling: {e}")
            self.omnik_api_level = 0
            # Abort retry later
            return None

    def _validate_field(self, data, field, fallback):
        # validate existance of field in dict
        # provide a default value if it is not available
        if data:
            if field not in data:
                data[field] = fallback

    def _validate_client_data(self, plant, data):
        # Insert defaults for missing fields
        # data['data']['plant_id']
        self._validate_field(data, 'inverter', self.config.get(f"plant.{plant}", 'inverter_sn', 'n/a'))
        return data

    def _output_update(self, plant, data):
        # Insert dummy data for fields that have not been supplied by the client
        data = self._validate_client_data(plant, data)
        # Process for each plugin, but only when valid
        for plugin in Plugin.plugins:
            if not plugin.process_aggregates or 'sys_id' in data:
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Trigger plugin '{getattr(plugin, 'name')}'.")
                plugin.process(msg=data)

    def _output_update_aggregated_data(self, plant, data):
        # Insert dummy data for fields that have not been supplied by the client
        data = self._validate_client_data(plant, data)
        # Process for each plugin, but only when valid
        for plugin in Plugin.plugins:
            if plugin.process_aggregates:
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Trigger plugin '{getattr(plugin, 'name')}' with aggregated data.")
                plugin.process(msg=data)

    def _init_aggregated_data(self, aggregated_data, data, sys_id):
        if not aggregated_data:
            # Initialize
            aggregated_data['sys_id'] = sys_id
            self._init_aggregated_data_field(aggregated_data, data, 'last_update')
            self._init_aggregated_data_field(aggregated_data, data, 'current_power')
            self._init_aggregated_data_field(aggregated_data, data, 'today_energy')
            self._init_aggregated_data_field(aggregated_data, data, 'total_energy')
            self._init_aggregated_data_field(aggregated_data, data, 'voltage_ac1')
            self._init_aggregated_data_field(aggregated_data, data, 'voltage_ac2')
            self._init_aggregated_data_field(aggregated_data, data, 'voltage_ac3')
            self._init_aggregated_data_field(aggregated_data, data, 'voltage_ac_max')
            self._init_aggregated_data_field(aggregated_data, data, 'inverter_temperature')
            if self.dsmr:
                self._init_aggregated_data_field(aggregated_data, data, 'power_consumption')
                self._init_aggregated_data_field(aggregated_data, data, 'energy_used')
                self._init_aggregated_data_field(aggregated_data, data, 'energy_used_net')
                self._init_aggregated_data_field(aggregated_data, data, 'net_voltage_max')
                self._init_aggregated_data_field(aggregated_data, data, 'INSTANTANEOUS_VOLTAGE_L1')
                self._init_aggregated_data_field(aggregated_data, data, 'INSTANTANEOUS_VOLTAGE_L2')
                self._init_aggregated_data_field(aggregated_data, data, 'INSTANTANEOUS_VOLTAGE_L3')

    def _init_aggregated_data_field(self, aggregated_data, data, field):
        if field in data:
            aggregated_data[field] = Decimal('0')

    def _adapt_max_value(self, aggregated_data, data, field):
        if field in data:
            if data[field] > aggregated_data[field]:
                aggregated_data[field] = data[field]

    def _adapt_add_value(self, aggregated_data, data, field):
        if field in data:
            aggregated_data[field] += data[field]

    def _aggregate_data(self, aggregated_data, data):
        # Check for pvoutput sys_id override in config
        sys_id = int(self.config.get(f"plant.{data['plant_id']}", 'sys_id', '0'))
        global_sys_id = int(self.config.get('output.pvoutput', 'sys_id', '0'))
        if sys_id and (sys_id != global_sys_id):
            # Do no aggegate: add sys_id to data set
            data['sys_id'] = sys_id
        else:
            # Get sys_id from pvoutput section, cannot aggregate without sys_id
            sys_id = global_sys_id
            if sys_id:
                # Aggerate data (initialize dict and set sys_id)
                self._init_aggregated_data(aggregated_data, data, sys_id)
                # Timestamp
                self._adapt_max_value(aggregated_data, data, 'last_update')
                # Add energy
                self._adapt_add_value(aggregated_data, data, 'today_energy')
                self._adapt_add_value(aggregated_data, data, 'total_energy')
                # Add power
                self._adapt_add_value(aggregated_data, data, 'current_power')
                # Max voltage
                self._adapt_max_value(aggregated_data, data, 'voltage_ac_max')
                self._adapt_max_value(aggregated_data, data, 'voltage_ac1')
                self._adapt_max_value(aggregated_data, data, 'voltage_ac2')
                self._adapt_max_value(aggregated_data, data, 'voltage_ac3')
                self._adapt_max_value(aggregated_data, data, 'net_voltage_max')
                self._adapt_max_value(aggregated_data, data, 'INSTANTANEOUS_VOLTAGE_L1')
                self._adapt_max_value(aggregated_data, data, 'INSTANTANEOUS_VOLTAGE_L2')
                self._adapt_max_value(aggregated_data, data, 'INSTANTANEOUS_VOLTAGE_L3')
                # Max inverter temperature
                self._adapt_max_value(aggregated_data, data, 'inverter_temperature')
            if sys_id and self.dsmr:
                self._adapt_add_value(aggregated_data, data, 'power_consumption')
                self._adapt_add_value(aggregated_data, data, 'energy_used_net')
                self._adapt_add_value(aggregated_data, data, 'energy_used')

    def _digitize(self, data):
        digitize_fields = [
            "current_power",
            "today_energy",
            "total_energy",
            "inverter_temperature",
            "current_ac1",
            "current_ac2",
            "current_ac3",
            "voltage_ac1",
            "voltage_ac2",
            "voltage_ac3",
            "voltage_ac_max",
            "frequency_ac1",
            "frequency_ac2",
            "frequency_ac3",
            "power_ac1",
            "power_ac2",
            "power_ac3",
            "current_pv1",
            "current_pv2",
            "current_pv3",
            "voltage_pv1",
            "voltage_pv2",
            "voltage_pv3",
            "power_pv1",
            "power_pv2",
            "power_pv3",
            "current_power_pv",
            "operation_hours"
            ]
        for field in data:
            if field in digitize_fields:
                data[field] = Decimal(f'{data[field]}')
        # Re calculate total enery for today accuracy (TODO per plant_id!) update after every measurement
        # store in cache and make persistant
        # Also store the last current power to the cache
        data['total_energy_recalc'] = self.total_energy(data['plant_id'],
                                                        today_energy=data['today_energy'],
                                                        total_energy=data['total_energy'],
                                                        current_power=data['current_power']
                                                        )

    def _load_persistant_cache(self):
        try:
            with open(self.persistant_cache_file) as total_energy_cache:
                file_cache = json.load(total_energy_cache)
                for item in file_cache:
                    self.cache[item] = Decimal(f"{file_cache[item]}")
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO",
                                f"Using energy cache file '{self.persistant_cache_file}'.")
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO",
                                f"Cache file '{self.persistant_cache_file}' was not used previously. Error: {e.args}")

    def _update_persistant_cache(self):
        try:
            file_cache = {}
            for item in self.cache:
                file_cache[item] = float(self.cache[item])
            with open(self.persistant_cache_file, 'w') as json_file_config:
                json.dump(file_cache, json_file_config)
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",
                                f"Cache file '{self.persistant_cache_file}' can not be written! Error: {e.args}")

    def last_current_power(self, plant):
        last_current_power = f'{plant}.last_current_power'
        if last_current_power not in self.cache:
            return Decimal('0')
        else:
            return self.cache[last_current_power]

    def total_energy(self, plant, today_energy=None, total_energy=None, current_power=None, lifetime=True):
        # start_total_energy_key = f'{plant}.start_total_energy'
        last_total_energy = f'{plant}.last_total_energy'
        last_today_energy = f'{plant}.last_today_energy'
        last_current_power = f'{plant}.last_current_power'
        # if total energy is supplied, update cache directly
        if total_energy:
            self.cache[last_total_energy] = total_energy
            self.cache[last_today_energy] = today_energy
            self.cache[last_current_power] = current_power
            self._update_persistant_cache()

        if plant not in self.start_total_energy:
            if total_energy:
                self.start_total_energy[plant] = total_energy - today_energy
                return self.start_total_energy[plant] + today_energy if lifetime else today_energy
            else:
                # No accurate total energy is available, use total_energy cache
                if last_today_energy in self.cache and last_total_energy in self.cache:
                    self.start_total_energy[plant] = self.cache[last_total_energy] - self.cache[last_today_energy]
                    return self.start_total_energy[plant] + self.cache[last_today_energy] if lifetime \
                        else self.cache[last_today_energy]
                else:
                    return None
        else:
            if total_energy and not today_energy:
                self.start_total_energy[plant] = total_energy
                return total_energy
            elif today_energy:
                return self.start_total_energy[plant] + today_energy
            else:
                if last_today_energy in self.cache and last_total_energy in self.cache:
                    return self.start_total_energy[plant] + self.cache[last_today_energy] if lifetime \
                        else self.cache[last_today_energy]
                else:
                    return None

    def _sunshine_check(self):
        self.sundown = not self.dl.sun_shine()
        if self.sundown:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO",
                                f"No sunshine postponing till down next dawn {self.dl.next_dawn}.")
            # Send 0 Watt update
            return self.dl.next_dawn + timedelta(minutes=10)
        else:
            # return the last report time return value, but not when there is no sun
            return self.last_update_time

    def _proces_pushed_net_event(self, plant_id, dsmr_message):

        # ts_midnight = datetime.combine(date.today(), datetime.min.time()).timestamp()
        data = deepcopy(dsmr_message)
        dsmr_timestamp = data['timestamp']
        # if (dsmr_timestamp - last_update) > (self.every + 10) and dsmr_timestamp > self.pasttime:
        if dsmr_timestamp > self.pasttime and plant_id and self.total_energy(plant_id):
            # Process independent net data for aggregated clients with regards of rate limits
            # data['current_power'] = Decimal('0')
            # Omnik related fields need 'last_update' timestamp
            data['last_update'] = dsmr_timestamp
            data['plant_id'] = plant_id
            data['total_energy_recalc'] = self.total_energy(plant_id)
            data['today_energy'] = self.total_energy(plant_id, lifetime=False)
            self._calculate_consumption(data)
            data['total_energy'] = data.pop('total_energy_recalc')
            aggegated_data = {}
            self._aggregate_data(aggegated_data, data)
            # Do not publish the current power
            # set next time block for update
            self.pasttime = dsmr_timestamp - (dsmr_timestamp % self.interval_aggregated) + self.interval_aggregated
            # set net updates out for aggegated clients (pvoutput)
            last_update = datetime.timestamp(self.plant_update[plant_id])
            if (dsmr_timestamp - last_update) > (self.every + 10) or not self.last_current_power(plant_id):
                self._process_received_update(aggegated_data, netdata=True, plant=plant_id)
                self._output_update_aggregated_data(plant_id, aggegated_data)
        # TODO process net update for other clients
        data2 = deepcopy(dsmr_message)
        data2['plant_id'] = plant_id
        self._validate_client_data(plant_id, data2)
        # data['last_update'] = dsmr_timestamp
        # data['net_update'] = True
        # dsmr_timestamp = data.pop('timestamp')
        # data['last_update'] = dsmr_timestamp
        # plant = self._process_received_update(data)
        # Set last update time for plant
        # self.plant_update[plant] = datetime.fromtimestamp(data['last_update'])
        # Digitize data
        # self._digitize(data)
        # Get dsmr data
        # self._get_dsmr_data(plant, data)
        # Assemble aggegated data
        # export the data to the output plugins
        self._output_update(plant_id, data2)
        # Process aggregated

    def _process_timed_event(self):
        # For portal clients and tcpclient with a fixed interval
        # Returns the date time of the last update (time behind) or a time in te future when postposing updates
        # Do a Sunshine check when a Timer is used
        next_report_at = self._sunshine_check()

        # Check for login, if needed. Return None on failure
        if not self._logon():
            # Logon failed
            # Sun is down, skip this measurement and wait till dawn
            return next_report_at if self.sundown else None

        # Caching of plant id's, if needed. Return None on failure
        if not self._fetch_plants():
            # Sun is down, skip this measurement and wait till dawn
            return next_report_at if self.sundown else None

        # Process data reports for each plant
        if self.omnik_api_level == 2:
            aggegated_data = {}
            for plant in self.plant_update:
                # Try getting a new update or wait for logging event
                data = self._fetch_update(plant)
                if data:
                    # A new last update time was set
                    if self.plant_update[plant] > next_report_at:
                        next_report_at = self.plant_update[plant]
                    # Digitize data
                    self._digitize(data)
                    # Get dsmr data
                    self._get_dsmr_data(plant, data)
                    # Assemble aggegated data
                    self._aggregate_data(aggegated_data, data)
                    # export the data to the output plugins
                    self._output_update(plant, data)
            # Process aggregated data
            if aggegated_data:
                self._output_update_aggregated_data(plant, aggegated_data)
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", 'Aggregated data processed.')

        # Finish datalogging process
        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", 'Timed data logging processed')

        # Return the the time of the latest report received
        return next_report_at

    def _process_pushed_event(self):
        # For localproxy client
        # Returns the date time of the last update
        next_report_at = None

        # Check for login, if needed. Return None on failure
        if not self._logon():
            # Skip this measurement, retry later
            return None

        # Caching of plant id's, if needed. Return None on failure
        if not self._fetch_plants():
            # Skip this measurement, retry later
            return None

        # Process data reports for each plant
        if self.omnik_api_level == 2:
            # Wait for new data logging event
            data = self._listen_for_update()
            if data:
                aggegated_data = {}
                plant = self._process_received_update(data)
                # Set last update time for plant
                self.plant_update[plant] = datetime.fromtimestamp(data['last_update'])
                # Digitize data
                self._digitize(data)
                # Get dsmr data
                self._get_dsmr_data(plant, data)
                # Assemble aggegated data
                self._aggregate_data(aggegated_data, data)
                # export the data to the output plugins
                self._output_update(plant, data)
                # Process aggregated
                self._output_update_aggregated_data(plant, aggegated_data)

        # Finish datalogging process
        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", 'Pushed logging processed')

        # Return the the time of the latest report received
        return next_report_at

    def process(self):
        # Returns the date time of the last update (time behind) or a time in te future when postposing updates
        # Do a Sunshine check when a Timer is used
        if self.client.use_timer:
            return self._process_timed_event()
        else:
            # Return None when an error occurs
            return self._process_pushed_event()

    @staticmethod
    def __expand_path(path):
        """
        Expand relative path to absolute path.
        Args:
            path: file path
        Returns: absolute path to file
        """
        if os.path.isabs(path):
            return path
        else:
            return os.path.dirname(os.path.abspath(__file__)) + "/" + path
