from omnik.ha_logger import hybridlogger
import omnik.InverterMsg
from omnik.plugin_client import Client
from socket import socket, error as sockerror, AF_INET, SOCK_STREAM
import binascii
import re
from datetime import datetime
import time
from decimal import Decimal
from requests import Request, Session


class TCPclient(Client):

    # IMPORTANT : ONLY WIFI Modules with s/n 602xxxxxx and 604xxxxxx support direct access thru port 8899!
    # For certain models it is possible to readout http:/{inverter_ip}:80/js/status.js If access through 8899 fails this method will be used as fall back method.
    # Based on: https://github.com/woutrrr/omnik-data-logger by Wouter van der Zwan
    # The script was tested only using simulations, let me know if this works for you

    def __init__(self):
        super().__init__()
        hybridlogger.ha_log(
            self.logger, self.hass_api, "INFO", "Client enabled: TCPclient"
        )

        # Get plant_id_list
        self.plant_id_list = self.config.getlist(
            "client.tcpclient", "plant_id_list", fallback=[]
        )
        if not self.plant_id_list:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                "plant_id_list was not specified for client TCPclient",
            )
            raise Exception("plant_id_list was not specified")
        # Initialize dict with inverter info
        self.inverters = {}
        self.session = {}

        # self._mode indicates the access mode that will be used
        # 0: Not initialized
        # 1: Running in native mode (port 8899)
        # 2: Running in fallback mode (port 80) fetching http://{inverter_ip}:80/js/status.js
        self._mode = {}

    def getPlants(self):
        data = []
        inverterdata = {}
        for plant in self.plant_id_list:
            inverter_address = self.config.get(
                f"plant.{plant}", "inverter_address", fallback=None
            )
            if not inverter_address:
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "ERROR",
                    f"inverter_address for plant {plant} was not specified [TCPclient]",
                )
                raise Exception("an inverter_address was not specified")
            inverter_port = int(
                self.config.get(f"plant.{plant}", "inverter_port", fallback="8899")
            )
            inverter_connection = (inverter_address, int(inverter_port))
            logger_sn = self.config.get(f"plant.{plant}", "logger_sn", fallback=None)
            http_only = bool(
                self.config.get(f"plant.{plant}", "http_only", fallback="False")
            )
            if not logger_sn:
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "ERROR",
                    "logger_sn (The serial number of the "
                    "Wi-Fi datalogger) for plant {plant} was not specified for [TCPclient], http mode only",
                )
            inverter_sn = self.config.get(
                f"plant.{plant}", "inverter_sn", fallback=None
            )
            if not inverter_sn:
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "WARNING",
                    "inverter_sn (The serial number of the inverter) "
                    "for plant {plant} was not specified for [TCPclient], http mode only",
                )
            inverterdata = {
                "inverter_address": inverter_address,
                "inverter_port": inverter_port,
                "logger_sn": int(logger_sn),
                "inverter_sn": inverter_sn,
                "inverter_connection": inverter_connection,
                "http_only": http_only,
            }
            self.inverters[plant] = inverterdata
            self._mode[plant] = 0
            data.append({"plant_id": plant})

        hybridlogger.ha_log(
            self.logger, self.hass_api, "DEBUG", f"plant list from config {data}"
        )

        return data

    def getPlantData(self, plant_id):
        data = None
        http_only = self.inverters[plant_id].get("http_only")
        if not self._mode.get(plant_id) and not http_only:
            # native mode
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"Initializing: Trying to reach the inverter for plant {plant_id} over port 8899.",
            )
        if (
            self._mode.get(plant_id) <= 1
            and self.inverters[plant_id].get("inverter_sn")
            and self.inverters[plant_id].get("logger_sn")
            and not http_only
        ):
            data = self._getPlantData_native(plant_id)
        if data:
            # set mode to native
            self._mode[plant_id] = 1
        if not self._mode:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"Initializing: Trying to reach the inverter for plant {plant_id} over port http (fallback).",
            )
        if self._mode.get(plant_id) == 0 or self._mode.get(plant_id) == 2:
            # fall back mode
            data = self._getPlantData_fallback(plant_id)

        return data

    def _getPlantData_native(self, plant_id):
        # Create a TCP/IP socket
        valid = False
        data = {}
        # Create request message
        requestmsg = omnik.InverterMsg.request_string(
            self.inverters[plant_id]["logger_sn"]
        )
        sock = socket(AF_INET, SOCK_STREAM)
        sock.settimeout(40)
        try:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "DEBUG",
                "Connecting to %s port %s"
                % self.inverters[plant_id]["inverter_connection"],
            )
            sock.connect(self.inverters[plant_id]["inverter_connection"])
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "DEBUG",
                "Sending request message with logger_sn: "
                f"{omnik.InverterMsg.request_string(self.inverters[plant_id]['logger_sn'])}",
            )
            # Sending request message
            sock.sendall(requestmsg)
            # Wait for response (listen and block thread)
            rawmsg = sock.recv(129)
            # Validate the data response. Check length and serial number
            if len(rawmsg) >= 99:
                inverterMsg = omnik.InverterMsg.InverterMsg(rawmsg)
                serialnr = inverterMsg.getID()
                # lookup plant_id to see it is in the plants list
                if self.inverters[plant_id]["inverter_sn"] == serialnr:
                    data["plant_id"] = plant_id
                    valid = True
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "DEBUG",
                    f"data size: {len(rawmsg)}.\n"
                    f"Datadump: {str(binascii.b2a_base64(rawmsg))}",
                )
        except sockerror as warn:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"Inverter is not reachable over port 8899, this is normal when it is dark. {warn}",
            )
            return None

        if valid:
            # Get the data from the received message
            inverterMsg.FetchDataDict(data)
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                f"New message received from inverter '{serialnr}'",
            )
        else:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                "Invalid response, ignoring message",
            )
            data = None

        return data

    def _getPlantData_fallback(self, plant_id):
        data = None
        # Get get url for debugging
        url = self.config.get(
            f"plant.{plant_id}",
            "url",
            fallback=f"http://{self.inverters[plant_id].get('inverter_address')}/js/status.js",
        )
        headers = {
            "User-Agent": "Omnikdatalogger",
            "Content-Type": "text/xml; charset=utf-8",
            "Connection": "keep-alive",
            "Accept": "Content-Type: text/html; charset=UTF-8",
        }
        if not self.session.get(plant_id):
            self.session[plant_id] = Session()
        request = Request("GET", url=url, headers=headers)
        prepped_request = self.session[plant_id].prepare_request(request)
        response = self.session[plant_id].send(prepped_request)
        # Throw if status is not valid
        response.raise_for_status()

        # We have response, lets validate it now
        inverter_data_search = re.search(
            r'(?<=webData=").*?(?=";)|(?<=myDeviceArray\[0\]=").*?(?=";)',
            response.content.decode("utf-8"),
        )
        if inverter_data_search:
            # Now extract our data (if valid)
            inverter_data = inverter_data_search.group(0).split(",")
            lastupdate = time.time()
            data = {
                "plant_id": plant_id,
                "last_update": lastupdate,
                "last_update_time": datetime.utcfromtimestamp(lastupdate).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "inverter": inverter_data[0],
                "current_power": Decimal(inverter_data[5]),
                "today_energy": Decimal(inverter_data[6]) / 100,
                "total_energy": Decimal(inverter_data[7]) / 10,
            }
            # set mode to http
            self._mode[plant_id] = 2
        return data
