import json
import requests

from omnik.plugin_output import Plugin


class influxdb(Plugin):

    def __init__(self):
        super().__init__()
        self.name = 'influxdb'
        self.description = 'Write output to InfluxDB'

    def get_weather(self):
        try:
            if 'weather' not in self.cache:
                self.logger.debug('[cache miss] Fetching weather data')
                url = "https://{endpoint}/data/2.5/weather?lon={lon}&lat={lat}&units={units}&APPID={api_key}".format(
                    endpoint=self.config.get('openweathermap', 'endpoint'),
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
            self.logger.error('Unable to get data. [{0}]: {1}'.format(
                type(e).__name__, str(e)))
            raise e

    def process(self, **args):
        # Send data to influxdb
        try:
            msg = args['msg']

            self.logger.debug(json.dumps(msg, indent=2))

            if not self.config.has_option('influxdb', 'database'):
                self.logger.error(
                    f'[{__name__}] No database found in configuration')
                return

            host = self.config.get('influxdb', 'host', fallback='localhost')
            port = self.config.get('influxdb', 'port', fallback='8086')
            database = self.config.get('influxdb', 'database')

            headers = {
                "Content-type": "application/x-www-form-urlencoded"
            }
            # Add JWT authentication token
            if self.config.has_option('influxdb', 'jwt_token'):
                headers['Authorization'] = f"Bearer {self.config.get('influxdb', 'jwt_token')}"
            elif self.config.has_option('influxdb', 'username') and self.config.has_option('influxdb', 'password'):
                auth = requests.auth.HTTPBasicAuth(self.config.get('influxdb', 'username'),
                                                   self.config.get('influxdb', 'password'))
                headers['Authorization'] = f"Bearer {self.config.get('influxdb', 'jwt_token')}"
            data = {}
            values = msg.copy()
            if self.config.getboolean('influxdb', 'use_temperature', fallback=False):
                weather = self.get_weather()
                values['temperature'] = str(weather['main']['temp'])

            if 'last_update_time' in values:
                values.pop('last_update_time')

            nanoepoch = int(
                values.pop('last_update') * 1000000000
            )
            # Build structure
            attributes = {
                "inverter": msg['inverter'],
                "plant_id": msg['plant_id']
                }
            encoded = ""
            for field in self.config.data_field_config:
                if field in values:
                    tags = attributes.copy()
                    tags['entity'] = field
                    tags['name'] = self.config.data_field_config[field]['name']
                    if self.config.data_field_config[field]['dev_cla']:
                        tags['dev_cla'] = self.config.data_field_config[field]['dev_cla']
                    if self.config.data_field_config[field]['dev_cla']:
                        tags['unit'] = self.config.data_field_config[field]['unit']
                    tags.update(self.config.data_field_config[field]['tags'])
                    data[field] = {
                        "measurement": self.config.data_field_config[field]['measurement'],
                        "tags": tags.copy(),
                        "value": msg[field]
                        }
                    # format output data using the InfluxDB line protocol
                    # https://v2.docs.influxdata.com/v2.0/write-data/#line-protocol
                    encoded += f'{data[field]["measurement"]},' \
                               f'{",".join("{}={}".format(key, value) for key, value in data[field]["tags"].items())} ' \
                               f'value={data[field]["value"]} {nanoepoch}\n'

            # Influx has no tables! Use measurement prefix
            # encoded = f'inverter,plant=p1 {",".join("{}={}".format(key, value)
            # for key, value in values.items())} {nanoepoch}'

            # curl -i -XPOST 'http://localhost:8086/write?db=mydb' --data-binary
            # 'cpu_load_short,host=server01,region=us-west value=0.64 1434055562000000000'
            url = f'http://{host}:{port}/write?db={database}'

            r = requests.post(url, data=encoded, headers=headers, auth=auth)

            r.raise_for_status()
            hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                f"Submit to Influxdb {url} successful.")
        except requests.exceptions.HTTPError as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",
                                f"Got error from influxdb: {str(e)} (ignoring: if this happens a lot ... fix it)")
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",
                                f"Got unknown submidding to influxdb: {str(e)} (ignoring: if this happens a lot ... fix it)")
