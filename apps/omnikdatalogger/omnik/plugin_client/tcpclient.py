from omnik.ha_logger import hybridlogger
import omnik.InverterMsg
from omnik.plugin_client import Client
import socket
import binascii


class TCPclient(Client):

    # IMPORTANT : ONLY WIFI Modules with s/n 602xxxxxx and 604xxxxxx support direct access thru port 8899!
    # Based on: https://github.com/woutrrr/omnik-data-logger by Wouter van der Zwan
    # The script was tested only using simulations, let me know if this works for you

    def __init__(self):
        super().__init__()
        hybridlogger.ha_log(self.logger, self.hass_api, "INFO", "Client enabled: TCPclient")

        # Get plant_id_list
        self.plant_id_list = self.config.getlist('client.tcpclient', 'plant_id_list', fallback=[])
        if not self.plant_id_list:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", "plant_id_list was not specified for client TCPclient")
            raise Exception('plant_id_list was not specified')
        # Initialize dict with inverter info
        self.inverters = {}

    def getPlants(self):
        data = []
        inverterdata = {}
        for plant in self.plant_id_list:
            inverter_address = self.config.get(f"plant.{plant}", 'inverter_address', fallback=None)
            if not inverter_address:
                hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",
                                    f"inverter_address for plant {plant} was not specified [TCPclient]")
                raise Exception('an inverter_address was not specified')
            inverter_port = int(self.config.get(f"plant.{plant}", 'inverter_port', fallback='8899'))
            inverter_connection = (inverter_address, int(inverter_port))
            logger_sn = self.config.get(f"plant.{plant}", 'logger_sn', fallback=None)
            if not logger_sn:
                hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", "logger_sn (The serial number of the "
                                    "Wi-Fi datalogger) for plant {plant} was not specified for [TCPclient]")
                raise Exception('logger_sn (a serial number f the Wi-Fi datalogger) was not specified')
            inverter_sn = self.config.get(f"plant.{plant}", 'inverter_sn', fallback=None)
            if not inverter_sn:
                hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", "inverter_sn (The serial number of the inverter) "
                                    "for plant {plant} was not specified for [TCPclient]")
                raise Exception('inverter_sn (a serial number of the inverter) was not specified')
            inverterdata = {
                "inverter_address": inverter_address,
                "inverter_port": inverter_port,
                "logger_sn": int(logger_sn),
                "inverter_sn": inverter_sn,
                "inverter_connection": inverter_connection
                }
            self.inverters[plant] = inverterdata
            data.append({'plant_id': plant})

        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", f"plant list from config {data}")

        return data

    def getPlantData(self, plant_id):

        valid = False
        data = {}
        # Create request message
        requestmsg = omnik.InverterMsg.request_string(self.inverters[plant_id]['logger_sn'])
        # Create a TCP/IP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(40)
        try:
            hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", 'Connecting to %s port %s'
                                % self.inverters[plant_id]['inverter_connection'])
            sock.connect(self.inverters[plant_id]['inverter_connection'])
            hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", "Sending request message with logger_sn: "
                                f"{omnik.InverterMsg.request_string(self.inverters[plant_id]['logger_sn'])}")
            # Sending request message
            sock.sendall(requestmsg)
            # Wait for response (listen and block thread)
            rawmsg = sock.recv(129)
            # Validate the data response. Check length and serial number
            if len(rawmsg) >= 99:
                inverterMsg = omnik.InverterMsg.InverterMsg(rawmsg)
                serialnr = inverterMsg.getID()
                # lookup plant_id to see it is in the plants list
                if self.inverters[plant_id]['inverter_sn'] == serialnr:
                    data['plant_id'] = plant_id
                    valid = True
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", f"data size: {len(rawmsg)}.\n"
                                    f"Datadump: {str(binascii.b2a_base64(rawmsg))}")
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", f"Error getting data from inverter. {e}")
            return None

        if valid:
            # Get the data from the received message
            inverterMsg.FetchDataDict(data)
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO",
                                f"New message received from inverter '{serialnr}'")
        else:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", "Invalid response, ignoring message")
            data = None
        return data
