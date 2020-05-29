import os
import sys
import logging
from ha_logger import hybridlogger
import datetime
import requests
import daylight

from .plugin_output import Plugin
from .plugin_client import Client
# from .plugin_localproxy import LocalProxyPlugin

logger = logging.getLogger(__name__)


class DataLogger(object):

    def __init__(self, config, hass_api=None):
        # Defaults to UTC now() - every interval
        self.plant_update = {}
        self.config = config
        self.every = int(self.config.get('default', 'interval'))
        self.hass_api = hass_api
        self.logger = logger
        # Make sure we check for a recent update first
        self.last_update_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)

        # Initialize plugin paths
        sys.path.append(self.__expand_path('plugin_output'))
        sys.path.append(self.__expand_path('plugin_client'))
        sys.path.append(self.__expand_path('plugin_localproxy'))

        self.city = self.config.get('default', 'city', fallback='Amsterdam')
        try:
            self.dl = daylight.daylight(self.city)
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", f"City '{self.city}' not recognized. Error: {e}")
            sys.exit(1)

        if self.config.get('default', 'debug', fallback=False):
            logger.setLevel(logging.DEBUG)

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
            Client.config = config
            Client.hass_api = hass_api
            __import__(self.client_module)
            self.client = Client.client[0]
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "ERROR", f"Client '{self.client_module}' could not be initialized. Error: {e}")
            sys.exit(1)

        self.plugins = self.config.getlist('plugins', 'output', fallback=[''])
        if self.plugins[0]:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO", f"Plugins enabled: {self.plugins}.")
        else:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "WARNING", "No output plugins configured! Monitoring only.")
        # Import output plugins
        if self.plugins[0]:
            Plugin.logger = self.logger
            Plugin.config = config
            Plugin.hass_api = hass_api

            for plugin in self.plugins:
                __import__(plugin)

        self.omnik_api_level = 0

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
        self._validate_field(data, 'inverter', self.config.get('plants', str(plant), 'n/a'))
        return data

    def _output_update(self, plant, data):
        # Insert dummy data for fields that have not been supplied by the client
        data = self._validate_client_data(plant, data)
        # Process for each plugin, but only when valid
        for plugin in Plugin.plugins:
            hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                f"Trigger plugin '{getattr(plugin, 'name')}'.")
            plugin.process(msg=data)

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
            for plant in self.plant_update:
                # Try getting a new update or wait for logging event
                data = self._fetch_update(plant)
                if data:
                    # A new last update time was set
                    if self.plant_update[plant] > next_report_at:
                        next_report_at = self.plant_update[plant]
                    # export the data to the output plugins
                    self._output_update(plant, data)

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
                plant = self._process_received_update(data)
                # export the data to the output plugins
                self._output_update(plant, data)

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
