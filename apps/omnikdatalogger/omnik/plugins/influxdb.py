from omnik.plugins import Plugin
from ha_logger import hybridlogger


class influxdb(Plugin):

    def process(self, **args):
        self.logger.debug('Hello from influxdb')
