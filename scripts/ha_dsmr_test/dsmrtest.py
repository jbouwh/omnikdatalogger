#! /usr/bin/env python3

from dsmr_parser import telegram_specifications
from dsmr_parser.parsers import TelegramParser
from dsmr_parser.clients.telegram_buffer import TelegramBuffer
from dsmr_parser.exceptions import ParseError, InvalidChecksumError
from dsmr_parser.clients.settings import SERIAL_SETTINGS_V2_2, \
    SERIAL_SETTINGS_V4, SERIAL_SETTINGS_V5
import threading
import logging
import time
import socket
import serial

stopflag = False
logger = logging.getLogger(__name__)

try:
    # AppDeamon is only needed when run used with AppDaemon
    import appdaemon.plugins.hass.hassapi as hass
except ImportError:
    # AppDeamon is not needed when run in command mode uses dummy class
    class hass(object):
        Hass = object


class P1test(hass.Hass):

    def _logme(self, line):
        print(line)

    def initialize(self, *args, **kwargs):
        try:
            self.log("Using hass logger!")
        except Exception:
            self.log = self._logme
            self.log("Using test logger!")
        self.mode = 'tcp'
        self.host = 'homeassistant.fritz.box'
        self.port = 3333
        self.device = 'COM3'
        self.dsmr_version = '5'
        self.terminal_name = 'test'
        self.stop = False
        self.transport = None
        self.log("Starting thread...")
        self.log("P1 test started")
        parser = self.test_serial
        # parser = self.tcp

        dsmr_version = self.dsmr_version
        if dsmr_version == '2.2':
            specification = telegram_specifications.V2_2
            serial_settings = SERIAL_SETTINGS_V2_2
        elif dsmr_version == '4':
            specification = telegram_specifications.V4
            serial_settings = SERIAL_SETTINGS_V4
        elif dsmr_version == '5':
            specification = telegram_specifications.V5
            serial_settings = SERIAL_SETTINGS_V5
        elif dsmr_version == '5B':
            specification = telegram_specifications.BELGIUM_FLUVIUS
            serial_settings = SERIAL_SETTINGS_V5
        else:
            raise NotImplementedError("No telegram parser found for version: %s",
                                      dsmr_version)
        self.telegram_parser = TelegramParser(specification)
        self.serial_settings = serial_settings
        # buffer to keep incomplete incoming data
        self.telegram_buffer = TelegramBuffer()

        self.thr = threading.Thread(target=parser, daemon=True)
        self.thr.start()
        self.log("Started!")
        # logging.basicConfig(level=logging.DEBUG)

    def dsmr_serial_callback(self, telegram):
        self.log('Telegram received')

    def terminate(self):
        self.stop = True
        self.log("Closing transport...")
        if self.transport:
            self.transport.close()
        self.thr.join(10)
        # Stopping loop the hard
        if self.thr.is_alive():
            self.log("Stopping the loop unfortunally did not stop the thread, waiting for completion...")
        else:
            self.log("Thread exited nicely")
        self.thr.join()
        self.log("Thread has stopped!")

    def test_serial(self):
        s = serial.Serial(port=self.device, **self.serial_settings)
        while not self.stop:
            data = s.read_until()
            print(f'{data}')
            self.data_received(data)
        s.close()

    def test_tcp(self):
        server_address = (self.host, self.port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(server_address)
        while not self.stop:
            data = sock.recv(1024)
            self.data_received(data)

        sock.close()

    def data_received(self, data):
        """Add incoming data to buffer."""
        data = data.decode('ascii')
        self.telegram_buffer.append(data)

        for telegram in self.telegram_buffer.get_all():
            self.handle_telegram(telegram)

    def handle_telegram(self, telegram):
        """Send off parsed telegram to handling callback."""
        try:
            parsed_telegram = self.telegram_parser.parse(telegram)
        except InvalidChecksumError as e:
            self.log.warning(str(e))
        except ParseError:
            self.log.exception("failed to parse telegram")
        else:
            self.dsmr_serial_callback(parsed_telegram)


if __name__ == '__main__':
    hassinstance = P1test()
    hassinstance .initialize()
    # loop is for commandline execution only
    try:
        while not stopflag:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    hassinstance.terminate()
