import os
import sys
import logging
from datetime import datetime

from .plugins import Plugin

from .client import OmnikPortalClient

logger = logging.getLogger(__name__)

class DataLogger(object):

  def __init__(self, config, debug=False):
    self.config = config
    self.plugins = []

    if not self.config.has_option('omnikportal', 'username') or not self.config.has_option('omnikportal', 'password'):
      logger.error('No username/password for omnikportal found')
      sys.exit(1)

    if debug:
      logger.setLevel(logging.DEBUG)

    self.client = OmnikPortalClient(
      logger = logger,
      username = self.config.get('omnikportal', 'username'),
      password = self.config.get('omnikportal', 'password'),
    )
    self.client.initialize()

    self.plugins = self.config.getlist('plugins', 'output', fallback=[])

    if len(self.plugins) > 0:

      sys.path.append(self.__expand_path('plugins'))

      Plugin.logger = logger
      Plugin.config = config

      for plugin in self.plugins:
        __import__(plugin)

  def process(self):

    plants = self.client.getPlants()

    for plant in plants:
      data = self.client.getPlantData(plant['plant_id'])

      for plugin in Plugin.plugins:
        logger.debug("About to trigger plugin '{}'.".format(getattr(plugin, 'name')))
        plugin.process(msg=data)

    logger.info('done @ {}'.format(datetime.now().isoformat()))

  @staticmethod
  def __expand_path(path):
      """
      Expand relative path to absolute path.
      Args:
          path: file path
      Returns: absolute path to file
      """
      if os.path.isabs(path):
          return path
      else:
          return os.path.dirname(os.path.abspath(__file__)) + "/" + path
    

    