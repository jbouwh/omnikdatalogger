#! /usr/bin/env python3

from dsmr_parser import telegram_specifications
import threading
from dsmr_parser.clients import create_dsmr_reader, create_tcp_dsmr_reader
from dsmr_parser.parsers import TelegramParser
from dsmr_parser.clients.telegram_buffer import TelegramBuffer
import asyncio
from functools import partial
import logging
import time
import socket

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
        except Exception as e:
            self.log = self._logme
            self.log("Using test logger!")
        self.mode = 'tcp'
        self.host = 'homeassistant.fritz.box'
        self.port = 3333
        self.dsmr_version = '5'
        self.terminal_name = 'test'
        self.stop = False
        self.transport = None
        self.log("Starting thread...")
        self.thr = threading.Thread(target=self.test, daemon=True)
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

    def test(self):
        self.log("P1 test started")
        dsmr_version = self.dsmr_version
        if dsmr_version == '2.2':
            specification = telegram_specifications.V2_2
        elif dsmr_version == '4':
            specification = telegram_specifications.V4
        elif dsmr_version == '5':
            specification = telegram_specifications.V5
        elif dsmr_version == '5B':
            specification = telegram_specifications.BELGIUM_FLUVIUS
        else:
            raise NotImplementedError("No telegram parser found for version: %s",
                                      dsmr_version)
        self.telegram_parser = TelegramParser(specification)
        # callback to call on complete telegram
        self.telegram_callback = self.handle_telegram
        # buffer to keep incomplete incoming data
        self.telegram_buffer = TelegramBuffer()
        server_address = (self.host, self.port)
        #amount_expected = len(data)
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

    def test2(self):
        self.log("P1 test started")
        try:
            self.loop = asyncio.get_event_loop()
            self.log("Got existing event loop!")
        except Exception as e:
            self.loop = asyncio.new_event_loop()
            self.log("Created new event loop!")
        asyncio.set_event_loop(self.loop)
        try:
            if self.mode == 'tcp':
                create_connection = partial(create_tcp_dsmr_reader,
                                            self.host, self.port, self.dsmr_version,
                                            self.dsmr_serial_callback, loop=self.loop)
            elif self.mode == 'device':
                create_connection = partial(create_dsmr_reader,
                                            self.device, self.dsmr_version,
                                            self.dsmr_serial_callback, loop=self.loop)
        except Exception as e:
            self.log(e)
            return
        # create serial or tcp connection
        while not self.stop:
            try:
                self.conn = create_connection()
                self.transport, protocol = self.loop.run_until_complete(self.conn)
                # wait until connection it closed
                self.loop.run_until_complete(protocol.wait_closed())
                # wait 5 seconds before attempting reconnect
                if not self.stop:
                    self.loop.run_until_complete(asyncio.sleep(5))
                else:
                    self.log("We have received a stop signal!")
            except Exception as e:
                if self.stop:
                    self.log(f"DSMR terminal {self.terminal_name} was terminated. "
                             f"Status code:: {e.args}"
                             )
                else:
                    self.log(f"DSMR terminal {self.terminal_name} was interrupted "
                             f"and will be restarted in a few moments: {e.args}"
                             )
                    time.sleep(10)
        if hasattr(self, 'loop'):
            self.loop.close()
            self.log("Loop closed")


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
