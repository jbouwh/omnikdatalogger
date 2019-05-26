import os
import sys
import logging
from backports.configparser import NoOptionError
from plugins import Plugin

from .client import DataLoggerEth, DataLoggerWifi

logger = logging.getLogger(__name__)

class DataLogger(object):
  def __init__(self, config, debug=False):
    self.config = config
    self.plugins = []

    try:
      # First, init client
      if self.config.get('default', 'network') == 'wifi':
        self.client = DataLoggerWifi(logger, self.config, debug)
      else:
        self.client = DataLoggerEth(logger, self.config, debug)

      # Now, init plugins
      self.plugins = self.config.getlist('plugins', 'output')

      sys.path.append(self.__expand_path('plugins'))

      Plugin.logger = logger
      Plugin.config = config

      for plugin in self.plugins:
        logger.info('> Loading plugin ' + plugin)
        __import__(plugin)

    except NoOptionError:
      logger.warn('No plugins found (continue without)')

  def process(self):
    msg = self.client.get()

    for plugin in Plugin.plugins:
      plugin.process_message(msg=msg)

  @staticmethod
  def __expand_path(path):
      """
      Expand relative path to absolute path.
      Args:
          path: file path
      Returns: absolute path to file
      """
      logger.debug(path)
      if os.path.isabs(path):
          return path
      else:
          return os.path.dirname(os.path.abspath(__file__)) + "/" + path
    

    