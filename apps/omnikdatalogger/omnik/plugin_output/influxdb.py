import requests
from omnik.ha_logger import hybridlogger

from omnik.plugin_output import Plugin


class influxdb(Plugin):

    def __init__(self):
        super().__init__()
        self.name = 'influxdb'
        self.description = 'Write output to InfluxDB'
        self.host = self.config.get('output.influxdb', 'host', fallback='localhost')
        self.port = self.config.get('output.influxdb', 'port', fallback='8086')
        self.database = self.config.get('output.influxdb', 'database', fallback='omnikdatalogger')

        self.headers = {
            "Content-type": "application/x-www-form-urlencoded"
        }
        # Add JWT authentication token
        if self.config.has_option('output.influxdb', 'jwt_token'):
            self.auth = None
            self.headers['Authorization'] = f"Bearer {self.config.get('output.influxdb', 'jwt_token')}"
        elif self.config.has_option('output.influxdb', 'username') and self.config.has_option('output.influxdb', 'password'):
            self.auth = requests.auth.HTTPBasicAuth(self.config.get('output.influxdb', 'username'),
                                                    self.config.get('output.influxdb', 'password'))

    def _get_temperature(self, values):
        if self.config.getboolean('output.influxdb', 'use_temperature', fallback=False):
            weather = self.get_weather()
            values['temperature'] = str(weather['main']['temp'])

    def _get_attributes(self, values):
        attributes = {"plant_id": values['plant_id']}
        if 'inverter' in values:
            if values['inverter'] == 'n/a':
                values.pop('inverter')
            else:
                attributes['inverter'] = values.pop('inverter')
        return attributes.copy()

    def _get_tags(self, field, attributes):
        tags = attributes.copy()
        tags['entity'] = field
        tags['name'] = str(self.config.data_field_config[field]['name']).replace(' ', '\\ ')
        if self.config.data_field_config[field]['dev_cla']:
            tags['dev_cla'] = self.config.data_field_config[field]['dev_cla']
        if self.config.data_field_config[field]['unit']:
            tags['unit'] = str(self.config.data_field_config[field]['unit']).replace(' ', '\\ ')
        tags.update(self.config.data_field_config[field]['tags'])
        return tags.copy()

    def _format_output(self, field, attributes, values, nanoepoch):
        if field in values:
            # Get tags
            tags = self._get_tags(field, attributes)
            # format output data using the InfluxDB line protocol
            # https://v2.docs.influxdata.com/v2.0/write-data/#line-protocol
            return f'{self.config.data_field_config[field]["measurement"]},' \
                   f'{",".join("{}={}".format(key, value) for key, value in tags.items())} ' \
                   f'value={values[field]} {nanoepoch}\n'
        else:
            return ''

    def process(self, **args):
        # Send data to influxdb
        try:
            msg = args['msg']

            values = msg.copy()
            self._get_temperature(values)

            if 'last_update_time' in values:
                values.pop('last_update_time')

            nanoepoch = int(
                values.pop('last_update') * 1000000000
            )
            # Build structure
            attributes = self._get_attributes(values)
            encoded = ""
            for field in self.config.data_field_config:
                encoded += self._format_output(field, attributes, values, nanoepoch)

            # Influx has no tables! Use measurement prefix
            # encoded = f'inverter,plant=p1 {",".join("{}={}".format(key, value)
            # for key, value in values.items())} {nanoepoch}'

            # curl -i -XPOST 'http://localhost:8086/write?db=mydb' --data-binary
            # 'cpu_load_short,host=server01,region=us-west value=0.64 1434055562000000000'
            url = f'http://{self.host}:{self.port}/write?db={self.database}'

            r = requests.post(url, data=encoded, headers=self.headers, auth=self.auth)

            r.raise_for_status()
            hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                f"Submit to Influxdb {url} successful.")
        except requests.exceptions.HTTPError as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",
                                f"Got error from influxdb: {str(e)} (ignoring: if this happens a lot ... fix it)")
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",
                                f"Got unknown submitting to influxdb: {str(e)} (ignoring: if this happens a lot ... fix it)")
