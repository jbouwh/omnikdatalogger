import os
import sys
import logging
from ha_logger import hybridlogger
import datetime
import requests
import pytz
import omnik.daylight
import appdaemon.plugins.hass.hassapi as hass


from .plugins import Plugin

from .client import OmnikPortalClient

logger = logging.getLogger(__name__)

plant_update = {}

class DataLogger(object):
    def __init__(self, config, hass_api=None):
        #defaults to UTC now() - every interval
        self.config = config
        self.every = int(self.config.get('default','interval'))
        self.plugins = []
        self.hass_api=hass_api
        self.logger=logger
        #make shure we check for a recent update first
        self.last_update_time = datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(hours=1)

        if not self.config.has_option('omnikportal', 'username') or not self.config.has_option('omnikportal', 'password'):
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",'No username/password for omnikportal found')
            sys.exit(1)
        self.city = self.config.get('default', 'city', fallback='Amsterdam')
        try:
            self.dl=omnik.daylight.daylight(self.city)
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",f"City '{self.city}' not recognized. Error: {e}")
            sys.exit(1)
        
        if self.config.get('default','debug', fallback=False):
            logger.setLevel(logging.DEBUG)

        self.client = OmnikPortalClient(
            logger=self.logger,
            hass_api=self.hass_api,
            username=self.config.get('omnikportal', 'username'),
            password=self.config.get('omnikportal', 'password'),
        )

        self.plugins = self.config.getlist('plugins', 'output', fallback=[])
        if len(self.plugins) > 0:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO", f"Plugins enabled: {self.plugins}.")
        else:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", f"No output plugins configured! Monitoring only. No output!")

        if len(self.plugins) > 0:

            sys.path.append(self.__expand_path('plugins'))

            Plugin.logger = self.logger
            Plugin.config = config
            Plugin.hass_api = hass_api

            for plugin in self.plugins:
                __import__(plugin)

        self.omnik_api_level=0

    def validate_user_login(self):
        self.omnik_api_level=0
        try:
            self.client.initialize(logger)
            #Logged on
            self.omnik_api_level=1
        except requests.exceptions.RequestException as err:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",f"Request error during account validation omnik portal: {err}")
        except requests.exceptions.HTTPError as errh:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",f"HTTP error during account validation omnik portal: {errh}")
        except requests.exceptions.ConnectionError as errc:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",f"Connection error during account validation omnik portal: {errc}")
        except requests.exceptions.Timeout as errt:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",f"Timeout error during account validation omnik portal: {errt}")  
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",e)

    def process(self):
        if not self.dl.sun_shine():
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO", f"No sunshine postponing till down next dawn {self.dl.next_dawn}.")
            #Send 0 Watt update
            sundown=True
            retval=self.dl.next_dawn+datetime.timedelta(minutes=10)
        else:
            sundown=False
            retval=self.last_update_time
        #check for login
        if (self.omnik_api_level==0):
            self.validate_user_login()
            if (self.omnik_api_level==0):
                return None

        #caching of plant id's
        if (not plant_update or self.omnik_api_level==1):
            try:
                plants = self.client.getPlants(logger)
                for pid in plants:
                    plant_update[pid['plant_id']] = self.last_update_time.replace(tzinfo=pytz.timezone('UTC'))
                self.omnik_api_level=2
            except requests.exceptions.RequestException as err:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",f"Request error: {err}")
                self.omnik_api_level=0
                return None
            except requests.exceptions.HTTPError as errh:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",f"HTTP error: {errh}")
                self.omnik_api_level=0
                return None
            except requests.exceptions.ConnectionError as errc:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",f"Connection error: {errc}")
                self.omnik_api_level=0
                return None
            except requests.exceptions.Timeout as errt:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",f"Timeout error: {errt}")  
                self.omnik_api_level=0
                return None
            except Exception as e:
                hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",e)
                self.omnik_api_level=0
                return None

        if (self.omnik_api_level==2):
            for plant in plant_update:
                #TODO Try block
                try:
                    data = self.client.getPlantData(logger, plant)
                    if sundown:
                        data['current_power'] = 0.0
                    # get the actual report time from the omnik portal
                    newreporttime=datetime.datetime.strptime(data['last_update_time'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.timezone('UTC'))
                    # Only proces updates that occured after we started or start a single measurement (TODO)
                    if (newreporttime > plant_update[plant] or not self.every or sundown):
                        hybridlogger.ha_log(self.logger, self.hass_api, "INFO", f"Update for plant {plant} update at UTC {newreporttime}")
                        # the newest plant_update time will be used as a baseline to program the timer
                        self.last_update_time = newreporttime
                        #update the last report time return value, but not when there is no sun
                        if not sundown:
                            retval=self.last_update_time
                        #Store the plat_update time for each indiviual plant, update only if there is a new report available to avoid duplicates
                        plant_update[plant]= newreporttime
                        data['plant_id'] = plant
                        for plugin in Plugin.plugins:
                            hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",f"Trigger plugin '{getattr(plugin, 'name')}'.")
                            #TODO pass config?
                            plugin.process(msg=data)
                    else:
                        hybridlogger.ha_log(self.logger, self.hass_api, "INFO", f'No recent report update to process ...  Last report at UTC {newreporttime}')
                except requests.exceptions.RequestException as err:
                    hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",f"Request error: {err}")
                    self.omnik_api_level=1
                    #Abort retry later
                    return None
                except requests.exceptions.HTTPError as errh:
                    hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",f"HTTP error: {errh}")
                    self.omnik_api_level=1
                    #Abort retry later
                    return None
                except requests.exceptions.ConnectionError as errc:
                    hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",f"Connection error: {errc}")
                    self.omnik_api_level=1
                    #Abort retry later
                    return None
                except requests.exceptions.Timeout as errt:
                    hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",f"Timeout error: {errt}")  
                    self.omnik_api_level=1
                    #Abort retry later
                    return None
                except Exception as e:
                    hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",e)
                    self.omnik_api_level=1
                    #Abort retry later
                    return None


        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",f'Data logging processed')
        #Return the the time of the latest report received
        return retval

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
