from ha_logger import hybridlogger
from omnik.client import Client


class LocalProxy(Client):

    # TODO implementation of logging using a local proxy using https://github.com/Woutrrr/Omnik-Data-Logger
    # and https://github.com/t3kpunk/Omniksol-PV-Logger

    def __init__(self):
        super().__init__()
        hybridlogger.ha_log(self.logger, self.hass_api, "INFO", "Client enabled: localproxy")

    def initialize(self, logger):
        pass

    def getPlants(self, logger):
        data = {}

        return data

    def getPlantData(self, logger, plant_id):

        data = {}

        return None

