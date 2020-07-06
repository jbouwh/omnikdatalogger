#! /usr/bin/env python3

from dsmr_parser import telegram_specifications
from dsmr_parser.clients import SerialReader, SERIAL_SETTINGS_V5
import appdaemon.plugins.hass.hassapi as hass
import threading


class P1test(hass.Hass):

    def initialize(self, *args, **kwargs):
        self.stop = False
        self.thr = threading.Thread(target=self.test)
        self.thr.start()

    def terminate(self):
        self.stop = True 
        self.thr.join()


    def test(self):
        self.log("P1 test started")
        serial_reader = SerialReader(
        device='/dev/ttyUSB0',
        serial_settings=SERIAL_SETTINGS_V5,
        telegram_specification=telegram_specifications.V5
        )

        for telegram in serial_reader.read_as_object():
            self.log(f"{telegram}")  # see 'Telegram object' docs below

            if self.stop:
                break
