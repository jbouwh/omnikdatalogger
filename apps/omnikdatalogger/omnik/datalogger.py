import os
import sys
import logging
from ha_logger import hybridlogger
import datetime
import requests
import pytz
import daylight

from .plugins import Plugin
from .client import Client

logger = logging.getLogger(__name__)


class DataLogger(object):

    def __init__(self, config, hass_api=None):
        # Defaults to UTC now() - every interval
        self.plant_update = {}
        self.config = config
        self.every = int(self.config.get('default', 'interval'))
        self.plugins = []
        self.hass_api = hass_api
        self.logger = logger
        # Make sure we check for a recent update first
        self.last_update_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)

        self.city = self.config.get('default', 'city', fallback='Amsterdam')
        try:
            self.dl = daylight.daylight(self.city)
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", f"City '{self.city}' not recognized. Error: {e}")
            sys.exit(1)

        if self.config.get('default', 'debug', fallback=False):
            logger.setLevel(logging.DEBUG)

        self.client_module = self.config.get('default', 'client', 'solarmanpv')
        hybridlogger.ha_log(self.logger, self.hass_api, "INFO", f"Initializing client : {self.client_module}.")
        sys.path.append(self.__expand_path('client'))
        Client.logger = self.logger
        Client.config = config
        Client.hass_api = hass_api
        __import__(self.client_module)
        self.client = Client.client[0]

        self.plugins = self.config.getlist('plugins', 'output', fallback=[])
        if len(self.plugins) > 0:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO", f"Plugins enabled: {self.plugins}.")
        else:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "WARNING", "No output plugins configured! Monitoring only.")
        # Import output plugins
        if len(self.plugins) > 0:
            sys.path.append(self.__expand_path('plugins'))

            Plugin.logger = self.logger
            Plugin.config = config
            Plugin.hass_api = hass_api

            for plugin in self.plugins:
                __import__(plugin)

        self.omnik_api_level = 0

    def _validate_user_login(self):
        self.omnik_api_level = 0
        try:
            self.client.initialize(logger)
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
                plants = self.client.getPlants(logger)
                for pid in plants:
                    self.plant_update[pid['plant_id']] = self.last_update_time.replace(tzinfo=pytz.timezone('UTC'))
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

    def _fetch_update(self, plant):
        try:
            data = self.client.getPlantData(logger, plant)
            if self.sundown:
                data['current_power'] = 0.0
            # Get the actual report time from the omnik portal
            newreporttime = datetime.datetime.strptime(data['last_update_time'],
                                                       '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.timezone('UTC'))
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
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", e)
            self.omnik_api_level = 0
            # Abort retry later
            return None

    def _output_update(self, data):
        # Process for each plugin, but only when valid
        for plugin in Plugin.plugins:
            hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                f"Trigger plugin '{getattr(plugin, 'name')}'.")
            plugin.process(msg=data)

    def process(self):
        # Returns the date time of the last update (time behind) or a time in te future when postposing updates.
        # Returns None when an error occurs

        # Sunshine check
        self.sundown = not self.dl.sun_shine()
        if self.sundown:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO",
                                f"No sunshine postponing till down next dawn {self.dl.next_dawn}.")
            # Send 0 Watt update
            next_report_at = self.dl.next_dawn + datetime.timedelta(minutes=10)
        else:
            # return the last report time return value, but not when there is no sun
            next_report_at = self.last_update_time

        # Check for login, if needed. Return None on failure
        if not self._logon():
            # Logon failed
            if self.sundown:
                # Sun is down, skip this measurement and wait till dawn
                return next_report_at
            else:
                # Skip this measurement, retry later
                return None

        # Caching of plant id's, if needed. Return None on failure
        if not self._fetch_plants():
            if self.sundown:
                return next_report_at
            else:
                return None

        # Process data reports for each plant
        if (self.omnik_api_level == 2):
            for plant in self.plant_update:
                # Try getting a new update
                data = self._fetch_update(plant)
                if data:
                    # A new last update time was set
                    if self.plant_update[plant] > next_report_at:
                        next_report_at = self.plant_update[plant]
                    # export the data to the output plugins
                    self._output_update(data)

        # Finish datalogging process
        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", 'Data logging processed')

        # Return the the time of the latest report received
        return next_report_at

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
