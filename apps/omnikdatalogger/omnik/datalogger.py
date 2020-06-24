import os
import sys
import logging
from omnik.ha_logger import hybridlogger
import datetime
import requests
import json
from .daylight import daylight

from .plugin_output import Plugin
from .plugin_client import Client
# from .plugin_localproxy import LocalProxyPlugin

logger = logging.getLogger(__name__)


class DataLogger(object):

    def __init__(self, config, hass_api=None):
        # Defaults to UTC now() - every interval
        self.plant_update = {}
        self.hass_api = hass_api
        self.logger = logger
        self.config = config
        if self.config.get('default', 'debug', fallback=False):
            logger.setLevel(logging.DEBUG)

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
            sys.exit(1)
        # read data_fields
        try:
            with open(self.data_config_file) as json_file_config:
                self.config.data_field_config = json.load(json_file_config)
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",
                                "Error reading configuration file (data_fields.json). Exiting!")
            raise e
            sys.exit(1)

        self.every = self._get_interval()

        # Make sure we check for a recent update first
        self.last_update_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)

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
            __import__(self.client_module)
            self.client = Client.client[0]
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "ERROR", f"Client '{self.client_module}' could not be initialized. Error: {e}")
            sys.exit(1)

    def _init_output_plugins(self):
        self.plugins = self.config.getlist('plugins', 'output', fallback=[''])
        if self.plugins[0]:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO", f"Plugins enabled: {self.plugins}.")
        else:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "WARNING", "No output plugins configured! Monitoring only.")
        # Import output plugins
        if self.plugins[0]:
            Plugin.logger = self.logger
            Plugin.config = self.config
            Plugin.hass_api = self.hass_api

            for plugin in self.plugins:
                __import__(plugin)

    def _get_interval(self):
        if self.config.has_option('default', 'interval'):
            return int(self.config.get('default', 'interval'))
        else:
            return 0

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
                    self.plant_update[pid['plant_id']] = self.last_update_time
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

    def _process_received_update(self, data):
        # Get the report time
        newreporttime = datetime.datetime.fromtimestamp(data['last_update']).astimezone(datetime.timezone.utc)
        plant = data['plant_id']
        hybridlogger.ha_log(self.logger, self.hass_api, "INFO",
                            f"Update for plant {plant} update at UTC {newreporttime}")
        return plant

    def _sundown_reset_power(self, data):
        if self.client.use_timer:
            if self.sundown:
                data['current_power'] = 0

    def _fetch_update(self, plant):
        try:
            data = self.client.getPlantData(plant)
            if data:
                self._sundown_reset_power(data)
                # Get the actual report time from the omnik portal
                newreporttime = datetime.datetime.fromtimestamp(data['last_update']).astimezone(datetime.timezone.utc)
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
            if not plugin.process_aggregates:
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Trigger plugin '{getattr(plugin, 'name')}'.")
                plugin.process(msg=data)

    def _output_update_aggegated_data(self, plant, data):
        # Insert dummy data for fields that have not been supplied by the client
        data = self._validate_client_data(plant, data)
        # Process for each plugin, but only when valid
        for plugin in Plugin.plugins:
            if plugin.process_aggregates:
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Trigger plugin '{getattr(plugin, 'name')}' with aggregated data.")
                plugin.process(msg=data)

    def _init_aggregated_data(self, aggregated_data, sys_id):
        if not aggregated_data:
            # Initialize
            aggregated_data['sys_id'] = sys_id
            aggregated_data['last_update'] = 0
            aggregated_data['current_power'] = 0
            aggregated_data['today_energy'] = 0
            aggregated_data['total_energy'] = 0
            aggregated_data['voltage_ac1'] = 0
            aggregated_data['voltage_ac2'] = 0
            aggregated_data['voltage_ac3'] = 0
            aggregated_data['voltage_ac_max'] = 0
            aggregated_data['inverter_temperature'] = 0

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
            sys_id = self.config.get('output.pvoutput', 'sys_id', '')
            if sys_id:
                # Aggerate data (initialize dict and set sys_id)
                self._init_aggregated_data(aggregated_data, sys_id)
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
                # Max inverter temperature
                self._adapt_max_value(aggregated_data, data, 'inverter_temperature')

    def _sunshine_check(self):
        self.sundown = not self.dl.sun_shine()
        if self.sundown:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO",
                                f"No sunshine postponing till down next dawn {self.dl.next_dawn}.")
            # Send 0 Watt update
            return self.dl.next_dawn + datetime.timedelta(minutes=10)
        else:
            # return the last report time return value, but not when there is no sun
            return self.last_update_time

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
                    # Assemble aggegated data
                    self._aggregate_data(aggegated_data, data)
                    # export the data to the output plugins
                    self._output_update(plant, data)
            # Process aggregated data
            self._output_update_aggegated_data(plant, aggegated_data)

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
                # Assemble aggegated data
                self._aggregate_data(aggegated_data, data)
                # export the data to the output plugins
                self._output_update(plant, data)
                # Process aggregated
                self._output_update_aggegated_data(plant, aggegated_data)

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
