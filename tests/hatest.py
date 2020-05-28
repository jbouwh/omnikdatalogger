#! /usr/bin/env python

import appdaemon.plugins.hass.hassapi as hass

# Initialization test class for AppDaemon (homeassistant)
class OmnikDataLoggerTEST(hass.Hass):

    def initialize(self, *args, **kwargs):
        self.log("This is my HA_test app")
        self.log(f"My arguments: {args}")
        self.handle = self.listen_state(self.callback, 'binary_sensor.datalogger', attribute='data')


    def terminate(self):
        self.cancel_listen_state(self.handle)

    def callback(self, entity, attribute, old, new, kwargs):
        self.log(f"Call back: {entity}:{attribute} {kwargs}")
        self.log(f"Old data: {old}")
        self.log(f"New data: {new}")
