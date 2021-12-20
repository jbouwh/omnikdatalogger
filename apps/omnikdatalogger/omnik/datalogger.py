import os
import sys
import logging
import pytz

from omnik import LOGLEVEL
from requests.exceptions import RequestException
from omnik.ha_logger import hybridlogger
from omnik.plant import Plant
import requests
import json
from .daylight import daylight
import threading
from time import time, sleep
from decimal import Decimal
from datetime import datetime, timedelta, timezone

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
        self.every = self._get_interval()
        self.interval_aggregated = self._get_interval_aggregated()
        # Wait at least a polling interval before submitting net data without solar aggegation
        self.pasttime = time() + self.every
        tz = self.config.get("default", "timezone", fallback="Europe/Amsterdam")
        self.timezone = pytz.timezone(tz)

        self.dsmr_access = threading.Condition(threading.Lock())

        if self.config.get("default", "debug", fallback=False):
            logger.setLevel(logging.DEBUG)
        if self.config.get("default", "loglevel"):
            logger.setLevel(LOGLEVEL.get(self.config.get("default", "loglevel")))

        if not self._init_data_fields():
            sys.exit(1)
        # init energy cache
        # total_energy_cache.json
        self.persistant_cache_file = self.config.get(
            "default", "persistant_cache_file", fallback="./persistant_cache.json"
        )
        self._load_persistant_cache()
        # read data_fields
        try:
            with open(self.data_config_file) as json_file_config:
                self.config.data_field_config = json.load(json_file_config)
        except Exception as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                f"Error reading configuration file (data_fields.json). Exiting!. Error: {e.args}",
            )
            raise e

        # read attributes
        if not self._read_attributes():
            sys.exit(1)

        # Make sure we check for a recent update first
        self.last_update_time = datetime.now(timezone.utc) - timedelta(
            seconds=self.interval_aggregated
        )

        # Initialize plugin paths
        sys.path.append(self.__expand_path("plugin_output"))
        sys.path.append(self.__expand_path("plugin_client"))
        sys.path.append(self.__expand_path("plugin_localproxy"))

        self.city = self.config.get("default", "city", fallback="Amsterdam")
        try:
            self.dl = daylight(self.city)
        except Exception as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                f"City '{self.city}' not recognized. Error: {e}",
            )
            sys.exit(1)

        # Initialize client
        self._init_client()
        # Initialize output plugins
        self._init_output_plugins()

        self.omnik_api_level = 0

        # Init dsmr
        self._init_dsmr()

    def _init_data_fields(self):
        self.config.data_config_file_args = self.config.get(
            "default", "data_config", fallback=""
        )
        hybridlogger.ha_log(
            self.logger,
            self.hass_api,
            "DEBUG",
            f"Data configuration [args]: '{self.config.data_config_file_args}'.",
        )
        hybridlogger.ha_log(
            self.logger,
            self.hass_api,
            "DEBUG",
            f"Data configuration [path]: '{self.config.data_config_file_path}'.",
        )
        hybridlogger.ha_log(
            self.logger,
            self.hass_api,
            "DEBUG",
            f"Data configuration [shared]: '{self.config.data_config_file_shared}'.",
        )
        hybridlogger.ha_log(
            self.logger,
            self.hass_api,
            "DEBUG",
            f"Data configuration [cwd]: '{self.config.data_config_file_cwd}'.",
        )
        if self.config.configfile:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"Using configuration from '{self.config.configfile}'.",
            )

        if os.path.exists(self.config.data_config_file_args):
            self.data_config_file = self.config.data_config_file_args
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"Using configured data configuration from '{self.data_config_file}'.",
            )
        elif os.path.exists(self.config.data_config_file_path):
            self.data_config_file = self.config.data_config_file_path
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"Using configured data configuration from '{self.data_config_file}'.",
            )
        elif os.path.exists(self.config.data_config_file_shared):
            self.data_config_file = self.config.data_config_file_shared
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"Using shared data configuration from '{self.data_config_file}'.",
            )
        elif os.path.exists(self.config.data_config_file_cwd):
            self.data_config_file = self.config.data_config_file_cwd
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"Using shared data configuration current working directory '{self.data_config_file}'.",
            )
        else:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                "No valid data configuration file (data_fields.json) found. Exiting!",
            )
            return False
        return True

    def _init_attribute_dict(self):
        self.config.attributes = {}
        asset_classes = list(
            ["omnik", "omnik_attributes", "omnik_dsmr", "dsmr", "dsmr_gas"]
        )
        self.config.attributes["asset"] = {
            "omnik": list(["inverter", "plant_id", "last_update"]),
            "omnik_attributes": list(["inverter", "plant_id", "last_update"]),
            "omnik_dsmr": list(
                ["inverter", "plant_id", "EQUIPMENT_IDENTIFIER", "last_update"]
            ),
            "dsmr": list(["EQUIPMENT_IDENTIFIER", "timestamp"]),
            "dsmr_gas": list(["EQUIPMENT_IDENTIFIER_GAS", "timestamp_gas"]),
        }
        self.config.attributes["model"] = {
            "omnik": "Omniksol",
            "omnik_attributes": "Omniksol",
            "omnik_dsmr": "Omnik data logger",
            "dsmr": "DSMR electicity meter",
            "dsmr_gas": "DSMR gas meter",
        }
        self.config.attributes["mf"] = {
            "omnik": "Omnik",
            "omnik_attributes": "Omnik",
            "omnik_dsmr": "JBsoft",
            "dsmr": "Netbeheer Nederland",
            "dsmr_gas": "Netbeheer Nederland",
        }
        self.config.attributes["identifier"] = {
            "omnik": "plant_id",
            "omnik_attributes": "plant_id",
            "omnik_dsmr": "plant_id",
            "dsmr": "EQUIPMENT_IDENTIFIER",
            "dsmr_gas": "EQUIPMENT_IDENTIFIER_GAS",
        }
        self.config.attributes["devicename"] = {
            "omnik": "Inverter",
            "omnik_attributes": "Inverter",
            "omnik_dsmr": "Omnik_data_logger",
            "dsmr": "DSMR_electicity_meter",
            "dsmr_gas": "DSMR_gasmeter",
        }
        self.config.attributes["device_identifier"] = {
            "omnik": "omnik",
            "omnik_attributes": "omnik",
            "omnik_dsmr": "omnik_dsmr",
            "dsmr": "dsmr",
            "dsmr_gas": "dsmr_gas",
        }
        return asset_classes

    def _init_attribute_set(self, attribute, asset_class, type="string"):
        if attribute not in self.config.attributes:
            self.config.attributes[attribute] = {}
        if not self.config.has_option("attributes", f"{attribute}.{asset_class}"):
            return
        if type == "list":
            self.config.attributes[attribute][asset_class] = self.config.getlist(
                "attributes", f"asset.{asset_class}"
            )
        else:
            self.config.attributes[attribute][asset_class] = self.config.get(
                "attributes", f"{attribute}.{asset_class}"
            )

    def _read_attributes(self):
        asset_classes = self._init_attribute_dict()
        try:
            if self.config.has_option("attributes", "asset_classes"):
                asset_classes += list(
                    set(self.config.getlist("attributes", "asset_classes"))
                    - set(asset_classes)
                )
            for asset_class in asset_classes:
                self._init_attribute_set("asset", asset_class, "list")
                self._init_attribute_set("model", asset_class)
                self._init_attribute_set("mf", asset_class)
                self._init_attribute_set("identifier", asset_class)
                self._init_attribute_set("devicename", asset_class)
        except Exception as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                f"Error reading attributes from config. Error: {e.args}",
            )
            raise e
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
        self.client_module = self.config.get("plugins", "client", None)
        if not self.client_module:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                "No 'client' parameter configured under the [plugin] section.",
            )
            sys.exit(1)

        hybridlogger.ha_log(
            self.logger,
            self.hass_api,
            "INFO",
            f"Initializing client : {self.client_module}.",
        )
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
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                f"Client '{self.client_module}' could not be initialized. Error: {e}",
            )
            sys.exit(1)

    def _terminate_client(self):
        while Client.client:
            Client.client.pop(0).terminate()

    def _init_output_plugins(self):
        self.plugins = self.config.getlist("plugins", "output", fallback=[""])
        if self.plugins and self.plugins[0]:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"Output plugins configured: {self.plugins}.",
            )
        else:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                "No output plugins configured! Monitoring only.",
            )
        # Import output plugins
        if self.plugins and self.plugins[0]:
            Plugin.logger = self.logger
            Plugin.config = self.config
            Plugin.hass_api = self.hass_api

            for plugin in self.plugins:
                try:
                    spec = importlib.util.find_spec(plugin)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                except AttributeError:
                    hybridlogger.ha_log(
                        self.logger,
                        self.hass_api,
                        "ERROR",
                        f"Output plugin {plugin} cannot be initialized!",
                    )

    def _terminate_output_plugins(self):
        while Plugin.plugins:
            Plugin.plugins.pop(0).terminate()

    def _init_dsmr(self):
        terminals = self.config.getlist("dsmr", "terminals", fallback=[])
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
        if "plant_id" not in data:
            data["plant_id"] = "0"
        if plant not in self.dsmr_data:
            return False
        while tries > 0:
            self.dsmr_access.acquire()
            if plant in self.dsmr_data:
                # Insert raw DSMR data
                data.update(self._dsmr_cache(plant, data["last_update"]))
                # Insert calculated netto values (solar - net)
                self._calculate_consumption(data)
                complete = True
            self.dsmr_access.release()
            tries -= 1
            if not complete:
                sleep(1)
            else:
                break
        if not tries:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                f"Could not match DSMR data. "
                "Did you configure your dsmr terminal correctly?",
            )
        return complete

    def _calculate_consumption(self, data):
        # Calculate cumulative energy direct used
        recalc_total = data.get("total_energy_recalc")
        if not recalc_total:
            recalc_total = data.get("total_energy")
        if not recalc_total:
            return
        data["energy_direct_use"] = (
            recalc_total - data["total_energy_offset"] - data["energy_delivered_net"]
        )
        data["energy_used"] = (
            data["energy_used_net"] + data["energy_direct_use"]
        )  # use as v3 * 1000 for pvoutput
        # Calculate the actual power used by adding the direct used power
        if "current_power" in data:
            data["power_direct_use"] = data["current_power"] - (
                data["CURRENT_ELECTRICITY_DELIVERY"] * Decimal("1000")
            )
            # Should not be negative, but timestamps can be out of sync.
            if data["power_direct_use"] < Decimal("0"):
                data["power_direct_use"] = Decimal("0")
            data["power_consumption"] = (
                data["CURRENT_ELECTRICITY_USAGE"] * Decimal("1000")
                + data["power_direct_use"]
            )
        else:
            # Since we have no sun power, there is no direct used power
            data["power_consumption"] = data["CURRENT_ELECTRICITY_USAGE"] * Decimal(
                "1000"
            )
            data["power_direct_use"] = Decimal("0")
        data["last_update_calc"] = time()

    def dsmr_callback(self, terminal, dsmr_message):
        # print(f"{dsmr_message['gas_consumption_totall']} =
        # m3 {dsmr_message['gas_consumption_hour']} m3/h - {dsmr_message['timestamp_gas']}")
        if dsmr_message["plant_id"]:
            plant_id = dsmr_message.pop("plant_id")
        else:
            plant_id = "0"
        self.dsmr_access.acquire()
        self._dsmr_cache_update(plant_id, dsmr_message)
        self.dsmr_access.release()
        if plant_id in self.plant_update:
            # DSMR for specific plant
            self._proces_pushed_net_event(plant_id, dsmr_message)
        else:
            # Aggregated DSMR only
            self._proces_pushed_net_event("0", dsmr_message)

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
            dsmr_ts = data["timestamp"]
            delta = abs(timestamp - dsmr_ts)
            if delta < max_delta or max_delta < 0:
                max_delta = delta
                best_data = data
        return best_data

    def _get_interval(self):
        if self.config.has_option("default", "interval"):
            return int(self.config.get("default", "interval"))
        else:
            return 0

    def _get_interval_aggregated(self):
        if self.config.has_option("default", "interval_aggregated"):
            return int(self.config.get("default", "interval_aggregated"))
        else:
            return 300

    def _validate_user_login(self):
        self.omnik_api_level = 0
        returnvalue = None
        try:
            returnvalue = self.client.initialize()
            # Logged on
            self.omnik_api_level = 1
            return returnvalue
        except RequestException as errc:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                f"Connection error during account validation omnik portal: {errc}",
            )
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", e)

    def _logon(self):
        # Log on to the omnik portal to enable fetching plant's
        if self.omnik_api_level == 0:
            if not self._validate_user_login() or self.omnik_api_level == 0:
                return False
        return True

    def _fetch_plants(self):
        # Fetch te plant's available for the account
        if not self.plant_update or self.omnik_api_level == 1:
            try:
                plants = self.client.getPlants()
                for pid in plants:
                    lastupdate = (
                        datetime.fromtimestamp(pid["last_update"]).astimezone(
                            timezone.utc
                        )
                        if pid.get("last_update")
                        else self.get_last_update(
                            str(pid["plant_id"]),
                            default=0.0,
                        )
                    )
                    self.plant_update[str(pid["plant_id"])] = Plant(
                        pid["plant_id"],
                        lastupdate,
                    )
                self.omnik_api_level = 2
            except requests.exceptions.RequestException as err:
                hybridlogger.ha_log(
                    self.logger, self.hass_api, "WARNING", f"Request error: {err}"
                )
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
        newreporttime = datetime.fromtimestamp(data["last_update"]).astimezone(
            timezone.utc
        )
        if not plant:
            plant = data["plant_id"]
        if plant == "0":
            updated_entities = "aggregated logging"
        else:
            updated_entities = f"plant {plant}"
        if netdata:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"Net data update for {updated_entities} UTC {newreporttime}",
            )
        else:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"Update for {updated_entities} UTC {newreporttime}",
            )

        return plant

    def _sundown_reset_power(self, data):
        if self.client.use_timer:
            if self.sundown:
                data["current_power"] = Decimal("0")

    def _fetch_update(self, plant):
        try:
            data = self.client.getPlantData(plant)
            if data:
                self._sundown_reset_power(data)
                # Get the actual report time from the omnik portal
                newreporttime = datetime.fromtimestamp(data["last_update"]).astimezone(
                    timezone.utc
                )
                # Only proces updates that occured after we started or start a single measurement
                # check for cached last update
                if (
                    newreporttime > self.plant_update[plant].last_update_time
                    or data["last_update"] > self.get_last_update(plant)
                    or not self.every
                    or self.sundown
                ):
                    hybridlogger.ha_log(
                        self.logger,
                        self.hass_api,
                        "INFO",
                        f"Update for plant {plant} UTC {newreporttime}",
                    )
                    # the newest plant_update time will be used as a baseline to program the timer
                    self.last_update_time = newreporttime
                    # Store the plant_update time for each indiviual plant,
                    # update only if there is a new report available to avoid duplicates
                    self.plant_update[
                        plant
                    ].last_update_time = newreporttime.astimezone(timezone.utc)
                    data["plant_id"] = plant
                    return data
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "INFO",
                    f"No recent report update to process aggregated data. Last report at UTC {newreporttime}",
                )
                return None

        except requests.exceptions.RequestException as err:
            hybridlogger.ha_log(
                self.logger, self.hass_api, "WARNING", f"Request error: {err}"
            )
            self.omnik_api_level = 0
            # Abort retry later
            return None
        except Exception as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                f"Unexpected error during data handling: {e}",
            )
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
        self._validate_field(
            data,
            "inverter",
            self.config.get(
                f"plant.{plant}", "inverter_sn", data.get("inverter") or "n/a"
            ),
        )
        if plant == "0":
            data["plant_id"] = "0"
        return data

    def _output_update(self, plant, data):
        # Insert dummy data for fields that have not been supplied by the client
        data = self._validate_client_data(plant, data)
        # Process for each plugin, but only when valid
        for plugin in Plugin.plugins:
            if (
                plugin.process_output
                or not plugin.process_aggregates
                or "sys_id" in data
            ):
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "DEBUG",
                    f"Trigger plugin '{getattr(plugin, 'name')}'.",
                )
                plugin.process(msg=data)

    def _output_update_aggregated_data(self, plant, data):
        # Insert dummy data for fields that have not been supplied by the client
        data = self._validate_client_data(plant, data)
        # Process for each plugin, but only when valid
        for plugin in Plugin.plugins:
            if plugin.process_aggregates:
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "DEBUG",
                    f"Trigger plugin '{getattr(plugin, 'name')}' with aggregated data.",
                )
                plugin.process(msg=data)

    def _init_aggregated_data(self, aggregated_data, data, sys_id):
        if not aggregated_data:
            # Initialize
            aggregated_data["sys_id"] = sys_id
            for field in [
                "last_update",
                "current_power",
                "today_energy",
                "total_energy",
                "current_ac1",
                "current_ac2",
                "current_ac3",
                "voltage_ac1",
                "voltage_ac2",
                "voltage_ac3",
                "voltage_ac_max",
                "inverter_temperature",
            ]:
                self._init_aggregated_data_field(aggregated_data, data, field)
            if data.get("cached"):
                aggregated_data["cached"] = True
            if self.dsmr:
                for field in [
                    # Attributes Electricity for pvoutput
                    "power_consumption",
                    "energy_used",
                    "energy_used_net",
                    "net_voltage_max",
                    "INSTANTANEOUS_VOLTAGE_L1",
                    "INSTANTANEOUS_VOLTAGE_L2",
                    "INSTANTANEOUS_VOLTAGE_L3",
                    # Other attributes Electricity for mqtt or influxdb
                    "timestamp",
                    "ELECTRICITY_USED_TARIFF_1",
                    "ELECTRICITY_USED_TARIFF_2",
                    "ELECTRICITY_DELIVERED_TARIFF_1",
                    "ELECTRICITY_DELIVERED_TARIFF_2",
                    "energy_delivered_net",
                    "CURRENT_ELECTRICITY_USAGE",
                    "CURRENT_ELECTRICITY_DELIVERY",
                    "ELECTRICITY_ACTIVE_TARIFF",
                    "LONG_POWER_FAILURE_COUNT",
                    "SHORT_POWER_FAILURE_COUNT",
                    "VOLTAGE_SAG_L1_COUNT",
                    "VOLTAGE_SAG_L2_COUNT",
                    "VOLTAGE_SAG_L3_COUNT",
                    "VOLTAGE_SWELL_L1_COUNT",
                    "VOLTAGE_SWELL_L2_COUNT",
                    "VOLTAGE_SWELL_L3_COUNT",
                    "INSTANTANEOUS_ACTIVE_POWER_L1_POSITIVE",
                    "INSTANTANEOUS_ACTIVE_POWER_L1_NEGATIVE",
                    "INSTANTANEOUS_ACTIVE_POWER_L2_POSITIVE",
                    "INSTANTANEOUS_ACTIVE_POWER_L2_NEGATIVE",
                    "INSTANTANEOUS_ACTIVE_POWER_L3_POSITIVE",
                    "INSTANTANEOUS_ACTIVE_POWER_L3_NEGATIVE",
                    "current_net_power",
                    "current_net_power_l1",
                    "current_net_power_l2",
                    "current_net_power_l3",
                    "net_voltage_max",
                    "INSTANTANEOUS_CURRENT_L1",
                    "INSTANTANEOUS_CURRENT_L2",
                    "INSTANTANEOUS_CURRENT_L3",
                    "net_current_l1",
                    "net_current_l2",
                    "net_current_l3",
                    # Other attributes Gas
                    "timestamp_gas",
                    "gas_consumption_total",
                    "gas_consumption_hour",
                ]:
                    self._init_aggregated_data_field(aggregated_data, data, field)
                # Other attributes Electricity
                # Other attributes Gas
                {
                    "timestamp_gas": 1622714706.0,
                    "gas_consumption_total": 2864.6,
                    "gas_consumption_hour": 0,
                }

    def _init_aggregated_data_field(self, aggregated_data, data, field):
        if field in data and field not in aggregated_data:
            aggregated_data[field] = Decimal("0")

    def _adapt_max_value(self, aggregated_data, data, field):
        if field in data:
            if data[field] > aggregated_data[field]:
                aggregated_data[field] = data[field]

    def _adapt_add_value(self, aggregated_data, data, field):
        if field in data:
            aggregated_data[field] += data[field]

    def _adapt_last_value(self, aggregated_data, data, field):
        if field in data:
            aggregated_data[field] = data[field]

    def _aggregate_data(self, aggregated_data, data):
        if not data:
            return
        # Check for pvoutput sys_id override in config
        sys_id = int(self.config.get(f"plant.{data['plant_id']}", "sys_id", "0"))
        global_sys_id = int(self.config.get("output.pvoutput", "sys_id", "0"))
        if sys_id and (sys_id != global_sys_id):
            # Do no aggegate: add sys_id to data set
            data["sys_id"] = sys_id
        else:
            # Get sys_id from pvoutput section, cannot aggregate without sys_id
            sys_id = global_sys_id
            # Aggerate data (initialize dict and set sys_id)
            self._init_aggregated_data(aggregated_data, data, sys_id)
            # Timestamp
            self._adapt_max_value(aggregated_data, data, "last_update")
            # Add energy
            self._adapt_add_value(aggregated_data, data, "today_energy")
            self._adapt_add_value(aggregated_data, data, "total_energy")
            # Add power
            self._adapt_add_value(aggregated_data, data, "current_power")
            # Max voltage
            self._adapt_max_value(aggregated_data, data, "voltage_ac_max")
            self._adapt_max_value(aggregated_data, data, "voltage_ac1")
            self._adapt_max_value(aggregated_data, data, "voltage_ac2")
            self._adapt_max_value(aggregated_data, data, "voltage_ac3")
            self._adapt_max_value(aggregated_data, data, "net_voltage_max")
            # Max current
            self._adapt_max_value(aggregated_data, data, "current_ac1")
            self._adapt_max_value(aggregated_data, data, "current_ac2")
            self._adapt_max_value(aggregated_data, data, "current_ac3")
            # Max inverter temperature
            self._adapt_max_value(aggregated_data, data, "inverter_temperature")
            if self.dsmr:
                self._adapt_add_value(aggregated_data, data, "power_consumption")
                self._adapt_add_value(aggregated_data, data, "energy_used_net")
                self._adapt_add_value(aggregated_data, data, "energy_used")
                # DSMR specific data for output to mqtt or influx with multiple meters or inverters
                self._adapt_max_value(aggregated_data, data, "INSTANTANEOUS_VOLTAGE_L1")
                self._adapt_max_value(aggregated_data, data, "INSTANTANEOUS_VOLTAGE_L2")
                self._adapt_max_value(aggregated_data, data, "INSTANTANEOUS_VOLTAGE_L3")
                # Other attributes Electricity for mqtt or influxdb
                self._adapt_last_value(aggregated_data, data, "timestamp")
                self._adapt_last_value(
                    aggregated_data, data, "ELECTRICITY_USED_TARIFF_1"
                )
                self._adapt_last_value(
                    aggregated_data, data, "ELECTRICITY_USED_TARIFF_2"
                )
                self._adapt_last_value(
                    aggregated_data, data, "ELECTRICITY_DELIVERED_TARIFF_1"
                )
                self._adapt_last_value(
                    aggregated_data, data, "ELECTRICITY_DELIVERED_TARIFF_2"
                )
                self._adapt_last_value(
                    aggregated_data, data, "ELECTRICITY_ACTIVE_TARIFF"
                )

                self._adapt_add_value(aggregated_data, data, "energy_delivered_net")
                self._adapt_add_value(
                    aggregated_data, data, "CURRENT_ELECTRICITY_USAGE"
                )
                self._adapt_add_value(
                    aggregated_data, data, "CURRENT_ELECTRICITY_DELIVERY"
                )
                self._adapt_add_value(aggregated_data, data, "LONG_POWER_FAILURE_COUNT")
                self._adapt_add_value(
                    aggregated_data, data, "SHORT_POWER_FAILURE_COUNT"
                )
                self._adapt_add_value(aggregated_data, data, "VOLTAGE_SAG_L1_COUNT")
                self._adapt_add_value(aggregated_data, data, "VOLTAGE_SAG_L2_COUNT")
                self._adapt_add_value(aggregated_data, data, "VOLTAGE_SAG_L3_COUNT")
                self._adapt_add_value(aggregated_data, data, "VOLTAGE_SWELL_L1_COUNT")
                self._adapt_add_value(aggregated_data, data, "VOLTAGE_SWELL_L2_COUNT")
                self._adapt_add_value(aggregated_data, data, "VOLTAGE_SWELL_L3_COUNT")

                self._adapt_add_value(
                    aggregated_data, data, "INSTANTANEOUS_ACTIVE_POWER_L1_POSITIVE"
                )
                self._adapt_add_value(
                    aggregated_data, data, "INSTANTANEOUS_ACTIVE_POWER_L2_POSITIVE"
                )
                self._adapt_add_value(
                    aggregated_data, data, "INSTANTANEOUS_ACTIVE_POWER_L3_POSITIVE"
                )
                self._adapt_add_value(
                    aggregated_data, data, "INSTANTANEOUS_ACTIVE_POWER_L1_NEGATIVE"
                )
                self._adapt_add_value(
                    aggregated_data, data, "INSTANTANEOUS_ACTIVE_POWER_L2_NEGATIVE"
                )
                self._adapt_add_value(
                    aggregated_data, data, "INSTANTANEOUS_ACTIVE_POWER_L3_NEGATIVE"
                )

                self._adapt_add_value(aggregated_data, data, "current_net_power")
                self._adapt_add_value(aggregated_data, data, "current_net_power_l1")
                self._adapt_add_value(aggregated_data, data, "current_net_power_l2")
                self._adapt_add_value(aggregated_data, data, "current_net_power_l3")
                self._adapt_add_value(aggregated_data, data, "INSTANTANEOUS_CURRENT_L1")
                self._adapt_add_value(aggregated_data, data, "INSTANTANEOUS_CURRENT_L2")
                self._adapt_add_value(aggregated_data, data, "INSTANTANEOUS_CURRENT_L3")
                self._adapt_add_value(aggregated_data, data, "net_current_l1")
                self._adapt_add_value(aggregated_data, data, "net_current_l2")
                self._adapt_add_value(aggregated_data, data, "net_current_l3")
                # Other attributes Gas
                self._adapt_last_value(aggregated_data, data, "timestamp_gas")

                self._adapt_add_value(aggregated_data, data, "gas_consumption_total")
                self._adapt_add_value(aggregated_data, data, "gas_consumption_hour")

    def _digitize_and_cache(self, data):
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
            "operation_hours",
        ]
        for field in data:
            if field in digitize_fields:
                data[field] = Decimal(f"{data[field]}")
        # Re calculate total energy for today accuracy per plant_id! update after every measurement
        # store in cache and make persistant
        # Also store the last current power to the cache
        plant = data.get("plant_id")
        if not plant:
            plant = "0"
        data["total_energy_recalc"] = self.total_energy(
            plant,
            today_energy=data.get("today_energy"),
            total_energy=data.get("total_energy"),
            current_power=data.get("current_power"),
            last_update=data.get("last_update"),
        )
        data["total_energy"] = data.pop("total_energy_recalc")

    def _load_persistant_cache(self):
        try:
            with open(self.persistant_cache_file) as total_energy_cache:
                file_cache = json.load(total_energy_cache)
                for item in file_cache:
                    try:
                        self.cache[item] = Decimal(f"{file_cache[item]}")
                    except:
                        self.cache[item] = file_cache[item]
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"Using energy cache file '{self.persistant_cache_file}'.",
            )
        except Exception as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"Cache file '{self.persistant_cache_file}' was not used previously. Error: {e.args}",
            )

    def _update_persistant_cache(self):
        try:
            file_cache = {}
            for item in self.cache:
                if type(self.cache[item]) == Decimal:
                    file_cache[item] = float(self.cache[item])
                else:
                    file_cache[item] = self.cache[item]
            with open(self.persistant_cache_file, "w") as json_file_config:
                json.dump(file_cache, json_file_config)
        except Exception as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                f"Cache file '{self.persistant_cache_file}' can not be written! Error: {e.args}",
            )

    def get_last_update(self, plant, default=time()):
        last_update_key = f"{plant}.last_update"
        cache = self.cache.get(last_update_key)
        if cache:
            return datetime.timestamp(datetime.strptime(cache, "%Y-%m-%dT%H:%M:%S"))
        return default

    def total_energy(
        self,
        plant,
        today_energy=None,
        total_energy=None,
        current_power=None,
        last_update=None,
        lifetime=True,
    ):
        # start_total_energy_key = f'{plant}.start_total_energy'
        last_total_energy = f"{plant}.last_total_energy"
        last_today_energy = f"{plant}.last_today_energy"
        last_current_power = f"{plant}.last_current_power"
        last_reset = f"{plant}.last_reset"
        last_update_key = f"{plant}.last_update"
        last_reset_payload = str(
            datetime.now(self.timezone)
            .replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            .isoformat()
        )
        # if total energy is supplied, update cache directly
        if total_energy:
            self.cache[last_total_energy] = total_energy
            self.cache[last_today_energy] = today_energy
            self.cache[last_current_power] = current_power
            self.cache[last_reset] = last_reset_payload
            self.cache[last_update_key] = str(
                datetime.fromtimestamp(last_update).replace(microsecond=0).isoformat()
            )
            self._update_persistant_cache()
        elif not self.cache.get(last_reset) or datetime.fromisoformat(
            last_reset_payload
        ) > datetime.fromisoformat(self.cache.get(last_reset)):
            # reset daily counters and last_reset
            self.cache[last_today_energy] = Decimal("0.0")
            self.cache[last_current_power] = Decimal("0.0")
            self.cache[last_reset] = str(last_reset_payload)
            if self.cache.get(last_total_energy):
                # reset initial energy in memory since today_energy is reset
                self.start_total_energy[plant] = self.cache.get(last_total_energy)
            self._update_persistant_cache()
            return self.cache[last_today_energy]

        if plant not in self.start_total_energy:
            if total_energy:
                self.start_total_energy[plant] = total_energy - today_energy
                return (
                    self.start_total_energy[plant] + today_energy
                    if lifetime
                    else today_energy
                )
            else:
                # No accurate total energy is available, use total_energy cache
                if last_today_energy in self.cache and last_total_energy in self.cache:
                    self.start_total_energy[plant] = (
                        self.cache[last_total_energy] - self.cache[last_today_energy]
                    )
                    return (
                        self.start_total_energy[plant] + self.cache[last_today_energy]
                        if lifetime
                        else self.cache[last_today_energy]
                    )
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
                    return (
                        self.start_total_energy[plant] + self.cache[last_today_energy]
                        if lifetime
                        else self.cache[last_today_energy]
                    )
                else:
                    return None

    def _sunshine_check(self):
        self.sundown = not self.dl.sun_shine()
        if self.sundown:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"No sunshine postponing till down next dawn {self.dl.next_dawn}.",
            )
            # Send 0 Watt update
            return self.dl.next_dawn + timedelta(minutes=10)
        else:
            # return the last report time return value, but not when there is no sun
            return self.last_update_time

    def _proces_pushed_net_event(self, plant_id, dsmr_message):

        data = deepcopy(dsmr_message)
        data["plant_id"] = plant_id
        self._validate_client_data(plant_id, data)
        dsmr_timestamp = data["timestamp"]
        last_solar_update = 0.0
        if dsmr_timestamp > self.pasttime:
            # Process independent net data for aggregated clients with regards of rate limits
            # Get last data from cache
            aggegated_data = {}
            if plant_id == "0":
                for plant in self.plant_update.keys():
                    if not self.total_energy(plant):
                        continue
                    cached_data = {}
                    cached_data["plant_id"] = plant
                    cached_data["last_update"] = self.get_last_update(plant, 0.0)
                    cached_data["total_energy"] = self.total_energy(plant)
                    cached_data["today_energy"] = self.total_energy(
                        plant, lifetime=False
                    )
                    # Assume we have no solar power currently
                    cached_data["current_power"] = Decimal("0.0")
                    self._aggregate_data(aggegated_data, cached_data)
                    cached_last_update = self.get_last_update(plant, 0.0)
                    if cached_last_update > last_solar_update:
                        last_solar_update = cached_last_update
                aggegated_data.update(data)
            elif self.total_energy(plant_id):
                cached_data = {}
                cached_data["plant_id"] = plant_id
                cached_data["last_update"] = self.get_last_update(plant_id, 0.0)
                cached_data["total_energy"] = self.total_energy(plant_id)
                cached_data["today_energy"] = self.total_energy(
                    plant_id, lifetime=False
                )
                # Assume we have no solar power currently
                cached_data["current_power"] = Decimal("0.0")
                self._aggregate_data(aggegated_data, cached_data)
                cached_last_update = self.get_last_update(plant_id, 0.0)
                if cached_last_update > last_solar_update:
                    last_solar_update = cached_last_update

            self.pasttime = (
                dsmr_timestamp
                - (dsmr_timestamp % self.interval_aggregated)
                + self.interval_aggregated
            )
            # proces net updates out for aggegated output (pvoutput) with (multiple) pushing inverters with aggegation and no updates
            last_update = 0.0
            if plant_id == "0":
                for plant in self.plant_update:
                    if (
                        datetime.timestamp(self.plant_update[plant].last_update_time)
                        > last_update
                    ):
                        last_update = datetime.timestamp(
                            self.plant_update[plant].last_update_time
                        )
            else:
                last_update = datetime.timestamp(
                    self.plant_update[plant_id].last_update_time
                )
            # we will send (net) updates when inverters do not retreive new updates
            if (dsmr_timestamp - last_update) > self.every:
                if aggegated_data:
                    data.update(aggegated_data)
                else:
                    data.update(cached_data)
                data["net_update"] = True
                # calculate energy_use
                self._calculate_consumption(data)
                self._process_received_update(data, netdata=True, plant=plant_id)
                target = f"for plant {plant_id} " if plant_id else ""
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "DEBUG",
                    f"Combining cached logging {target} with DSRM data.",
                )
                # update the output for aggregated logging
        # process net update for other clients
        self._output_update(plant_id, data)

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
            skip_aggregation = False
            for plant in self.plant_update:
                # Try getting a new update or wait for logging event
                data = self._fetch_update(plant)
                if data:
                    # A new last update time was set
                    if self.plant_update[plant].last_update_time > next_report_at:
                        next_report_at = self.plant_update[plant].last_update_time
                    # Digitize and cache inverter data and get a more accurate total_energy over the day using today_energy
                    self._digitize_and_cache(data)
                    # Get specific dsmr data
                    self._get_dsmr_data(plant, data)
                    # Assemble aggegated data
                    self._aggregate_data(aggegated_data, data)
                    # export the data to the output plugins
                    self._output_update(plant, data)
                else:
                    # Use cached data for aggregation with DSMR
                    data = {}
                    try:
                        data["cached"] = True
                        data["plant_id"] = plant
                        data["last_update"] = self.get_last_update(plant)
                        data["total_energy"] = self.total_energy(plant)
                        data["today_energy"] = self.total_energy(plant, lifetime=False)
                        # Assemble aggegated data
                        self._aggregate_data(aggegated_data, data)
                    except:
                        # do not allow data aggregation unless we have valid data
                        skip_aggregation = True

            # Process aggregated data over all plants if no specific plants are configured with DSMR terminal
            if aggegated_data and not skip_aggregation:
                # Output aggregated data to influx/mqtt if we have multiple plants
                if len(self.client.plant_id_list) > 1 or self._get_dsmr_data(
                    "0", aggegated_data
                ):
                    self._output_update("0", aggegated_data)
                self._output_update_aggregated_data(plant, aggegated_data)
                hybridlogger.ha_log(
                    self.logger, self.hass_api, "DEBUG", "Aggregated data processed."
                )

        # Finish datalogging process
        hybridlogger.ha_log(
            self.logger, self.hass_api, "DEBUG", "Timed data logging processed"
        )

        # Return the the time of the last report received
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

        # Process data reports for plant event data
        if self.omnik_api_level == 2:
            # Wait for new data logging event
            data = self._listen_for_update()
            if data:
                plant = self._process_received_update(data)
                # Set last update time for plant
                self.plant_update[plant].last_update_time = datetime.fromtimestamp(
                    data["last_update"], timezone.utc
                )
                # Digitize and cache inverter data and get a more accurate total_energy over the day using today_energy
                self._digitize_and_cache(data)
                # Get specific dsmr data
                self._get_dsmr_data(plant, data)
                # Cache last update for aggregation
                self.plant_update[plant].data = data
                # export the data to the output plugins
                self._output_update(plant, data)
        else:
            return next_report_at

        # To aggregate over multiple inverters we need to trigger publishing when we an update for all our inverters
        # Unless the last data update of an inverter is longer then 2 timed cycles
        aggegated_data = {}
        for published_plant in self.plant_update:
            if self.plant_update[published_plant].pop_for_aggregate(self.cache):
                # Assemble aggegated data
                self._aggregate_data(
                    aggegated_data, self.plant_update[published_plant].data
                )
            else:
                # Not ready yet to aggregate, erase cache
                aggegated_data = {}
                break
        # only publish unpublished fresh data (<10 minutes old)
        if aggegated_data:
            # Get dsmr data for aggegated data
            # Output aggregated data to influx/mqtt if we have multiple plants
            if len(self.client.plant_id_list) > 1 or self._get_dsmr_data(
                "0", aggegated_data
            ):
                self._output_update("0", aggegated_data)
            self._output_update_aggregated_data("0", aggegated_data)
            #
            hybridlogger.ha_log(
                self.logger, self.hass_api, "DEBUG", "Aggregated data processed"
            )
        elif data.get("sys_id"):
            # Export plant specific data without aggreation
            self._output_update_aggregated_data(data.get("plant_id"), data)
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "DEBUG",
                "Plant specific data aggregation processed",
            )

        # Finish datalogging process
        hybridlogger.ha_log(
            self.logger, self.hass_api, "DEBUG", "Pushed logging processed"
        )

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
