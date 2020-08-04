import requests
from cachetools import TTLCache
from omnik.ha_logger import hybridlogger
from decimal import Decimal

# TODO: Create Abstract Base Class


class BasePlugin(type):
    def __init__(cls, name, bases, attrs):
        super(BasePlugin, cls).__init__(name)
        if not hasattr(cls, 'plugins'):
            cls.plugins = []
        else:
            cls.register(cls)  # Called when a plugin class is imported

    def register(cls, plugin):
        cls.plugins.append(plugin())


class Plugin(object, metaclass=BasePlugin):

    config = None
    logger = None
    hass_api = None
    process_aggregates = False

    cache = TTLCache(maxsize=1, ttl=300)

    def jsonval(self, value):
        if isinstance(value, Decimal):
            if float(value) == int(value):
                return int(value)
            else:
                return float(value)
        elif isinstance(value, float):
            return value
        elif isinstance(value, int):
            return value
        elif isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value
        else:
            return str(value)

    def get_weather(self):
        try:
            if 'weather' not in self.cache:
                self.logger.debug('[cache miss] Fetching weather data')
                url = "https://{endpoint}/data/2.5/weather?lon={lon}&lat={lat}&units={units}&APPID={api_key}".format(
                    endpoint=self.config.get('openweathermap', 'endpoint', fallback='api.openweathermap.org'),
                    lat=self.config.get('openweathermap', 'lat'),
                    lon=self.config.get('openweathermap', 'lon'),
                    units=self.config.get(
                        'openweathermap', 'units', fallback='metric'),
                    api_key=self.config.get('openweathermap', 'api_key'),
                )

                res = requests.get(url)

                res.raise_for_status()

                self.cache['weather'] = res.json()

            return self.cache['weather']

        except requests.exceptions.HTTPError as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", 'Unable to get weather data. [{0}]: {1}'.format(
                                type(e).__name__, str(e)))
            raise e

    def process(self, **args):
        pass

    def terminate(self):
        pass
