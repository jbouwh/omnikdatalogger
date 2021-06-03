from omnik.ha_logger import hybridlogger
import omnik.InverterMsg
from omnik.plugin_client import Client
from omnik.plugin_localproxy import LocalProxyPlugin
import time
import threading
import importlib


class LocalProxy(Client):

    # TODO implementation of logging using a local proxy using https://github.com/Woutrrr/Omnik-Data-Logger
    # and https://github.com/t3kpunk/Omniksol-PV-Logger

    def __init__(self):
        super().__init__()

        hybridlogger.ha_log(
            self.logger, self.hass_api, "INFO", "Client enabled: localproxy"
        )

        # Switch of the repeated timer
        self.use_timer = False
        # Create a semaphore for unique access to the processing loop
        self.semaphore = threading.Semaphore()
        self.msgevent = threading.Event()
        self.msg = {"isSet": False, "data": None, "plugin": None}

        # Get plant_id_list
        self.plant_id_list = self.config.getlist(
            "client.localproxy", "plant_id_list", fallback=[""]
        )
        if not self.plant_id_list or self.plant_id_list[0] == "":
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                "plant_id_list was not specified for client localproxy",
            )
            raise Exception("plant_id_list was not specified")
        # Import localproxy plugins
        self.plugins = self.config.getlist("plugins", "localproxy", fallback=[""])
        if not self.plugins[0] == "":
            LocalProxyPlugin.semaphore = self.semaphore
            LocalProxyPlugin.logger = self.logger
            LocalProxyPlugin.config = self.config
            LocalProxyPlugin.hass_api = self.hass_api
            LocalProxyPlugin.client = self
            for plugin in self.plugins:
                # __import__(plugin)
                spec = importlib.util.find_spec(plugin)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
        else:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                "At least one plugin needs to be configured. "
                "No 'localproxy' plugins found at the [plugins] section.",
            )
            self.semaphore.release()
            raise Exception("No localproxy plugins were specified.")
        # Initialize dict with inverter info
        self.inverters = {}

    def terminate(self):
        # Stop all plugins
        # Claim the semaphore
        self.semaphore.acquire()
        while LocalProxyPlugin.localproxy_plugins:
            LocalProxyPlugin.localproxy_plugins.pop(0).terminate()
        # Release the semaphore
        self.semaphore.release()

    def getPlants(self):
        # Get the plant neeeded data from config
        data = []
        inverterdata = {}
        for plant in self.plant_id_list:
            inverter_sn = self.config.get(
                f"plant.{plant}", "inverter_sn", fallback=None
            )
            if not inverter_sn:
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "ERROR",
                    "inverter_sn (The serial number of the inverter) for "
                    f"plant {plant} was not specified for [TCPclient]",
                )
                raise Exception(
                    "inverter_sn (a serial number of the inverter) was not specified"
                )
            inverterdata = {"inverter_sn": inverter_sn}
            self.inverters[plant] = inverterdata
            data.append({"plant_id": plant})

        hybridlogger.ha_log(
            self.logger, self.hass_api, "DEBUG", f"plant list from config {data}"
        )

        # The config was read, start listening
        # Claim the semaphore
        self.semaphore.acquire()
        for plugin in LocalProxyPlugin.localproxy_plugins:
            plugin.listen()
        # Release the semaphore
        self.semaphore.release()
        return data

    def getPlantData(self, plant_id=None):
        # Wait here for a message
        self.msgevent.wait()
        # Claim the semaphore
        valid = False
        data = None
        self.semaphore.acquire()
        try:
            if self.msg["isSet"]:
                data = {}
                if self.msg["data"]:
                    if len(self.msg["data"]) == 128:
                        inverterMsg = omnik.InverterMsg.InverterMsg(self.msg["data"])
                        serialnr = inverterMsg.getID()
                        # lookup plant_id to see it is in the plants list
                        for plant in self.plant_id_list:
                            if self.inverters[plant]["inverter_sn"] == serialnr:
                                data["plant_id"] = plant
                                valid = True
                if valid:
                    # Get the data from the received message
                    inverterMsg.FetchDataDict(data)
                    hybridlogger.ha_log(
                        self.logger,
                        self.hass_api,
                        "INFO",
                        f"New message received from inverter '{serialnr}. Plugin: {self.msg['plugin']}'",
                    )
                else:
                    hybridlogger.ha_log(
                        self.logger,
                        self.hass_api,
                        "WARNING",
                        "Invalid response, ignoring message",
                    )
                    data = None

                # Reset isSet flag
                self.msg["isSet"] = False

        except Exception as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                f"Error occured while processing message. Error: {e}",
            )
        # Release the semaphore and event
        self.semaphore.release()
        self.msgevent.clear()
        # take some sleep to relax
        time.sleep(1)
        return data
