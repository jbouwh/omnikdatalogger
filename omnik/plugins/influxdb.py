from omnik.plugins import Plugin

class influxdb(Plugin):

  def process(self, **args):
    self.logger.info('Hello from influxdb')