from omnik.plugins import Plugin
from ha_logger import hybridlogger


class influxdb(Plugin):

    def process(self, **args):
        hybridlogger.ha_log(self.logger, self.hass_api, "INFO", "Hello from influxdb")