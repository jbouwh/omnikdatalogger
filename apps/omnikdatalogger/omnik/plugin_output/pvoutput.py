import json
import time
from omnik.ha_logger import hybridlogger

import urllib.parse
import requests
from omnik.plugin_output import Plugin


class pvoutput(Plugin):

    def __init__(self):
        super().__init__()
        self.name = 'pvoutput'
        self.description = 'Write output to PVOutput'
        # Enable support for aggregates
        self.process_aggregates = True

    def _get_temperature(self, msg, data):
        if self.config.getboolean('output.pvoutput', 'use_temperature', fallback=False):
            if self.config.getboolean('output.pvoutput', 'use_inverter_temperature', fallback=False) and \
                    ('inverter_temperature' in msg):
                data['v5'] = msg['inverter_temperature']
            else:
                weather = self.get_weather()

                data['v5'] = weather['main']['temp']

    def _get_voltage(self, msg, data):
        voltage_field = self.config.get('output.pvoutput', 'publish_voltage', fallback=None)
        if voltage_field:
            if voltage_field in msg:
                data['v6'] = msg[voltage_field]

    def process(self, **args):
        """
        Send data to pvoutput
        """
        try:
            msg = args['msg']
            reporttime = time.localtime(msg['last_update'])

            self.logger.debug(json.dumps(msg, indent=2))

            if not self.config.has_option('output.pvoutput', 'api_key'):
                hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",
                                    f'[{__name__}] No api_key found in configuration')
                return

            if 'sys_id' not in msg:
                hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",
                                    f'[{__name__}] No sys_id found in dataset, set sys_id under '
                                    'your plant settings or global under the pvoutpt section')
                return

            headers = {
                "X-Pvoutput-Apikey": self.config.get('output.pvoutput', 'api_key'),
                "X-Pvoutput-SystemId": str(msg['sys_id']),
                "Content-type": "application/x-www-form-urlencoded",
                "Accept": "text/plain"
            }

            # see: https://pvoutput.org/help.html
            # see: https://pvoutput.org/help.html#api-addstatus
            data = {
                'd': time.strftime('%Y%m%d', reporttime),
                't': time.strftime('%H:%M', reporttime),
                'v1': (msg['today_energy'] * 1000.0),
                'v2': msg['current_power'],
                'c1': 0
            }

            # Publish inverter temperature is available or use the temperature from openweather
            self._get_temperature(msg, data)

            # Publish voltage (if available)
            self._get_voltage(msg, data)

            encoded = urllib.parse.urlencode(data)

            self.logger.debug(json.dumps(data, indent=2))

            r = requests.post(
                "http://pvoutput.org/service/r2/addstatus.jsp", data=encoded, headers=headers)

            r.raise_for_status()

        except requests.exceptions.RequestException as err:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", f"Unhandled request error: {err}")
        except requests.exceptions.HTTPError as errh:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", f"Http error: {errh}")
        except requests.exceptions.ConnectionError as errc:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", f"Connection error: {errc}")
        except requests.exceptions.Timeout as errt:
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", f"Timeout error: {errt}")
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", e)
