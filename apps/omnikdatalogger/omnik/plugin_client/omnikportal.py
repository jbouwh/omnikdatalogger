import requests
import urllib.parse
from omnik.ha_logger import hybridlogger
from omnik.plugin_client import Client
from datetime import datetime


class OmnikPortalClient(Client):

    def __init__(self):
        super().__init__()
        hybridlogger.ha_log(self.logger, self.hass_api, "INFO", "Client enabled: omnikportalclient")

        # API Key's
        self.app_id = self.config.get('client.omnikportal', 'app_id', fallback='10038')
        self.app_key = self.config.get('client.omnikportal', 'app_key', fallback='Ox7yu3Eivicheinguth9ef9kohngo9oo')
        self.user_id = -1

        self.base_url = self.config.get('client.omnikportal', 'base_url', fallback='https://api.omnikportal.com/v1')

        self.username = self.config.get('client.omnikportal', 'username')
        self.password = self.config.get('client.omnikportal', 'password')

    def initialize(self):
        url = f'{self.base_url}/user/account_validate'

        body = {
            'user_email': self.username,
            'user_password': self.password,
            'user_type': 1
        }

        data = self._api_request(url, 'POST', body)
        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", f"account validation: {data}")

        # this is what `initialize` does ... setting the `user_id`
        self.user_id = data['data']['c_user_id']

    def _api_request(self, url, method, body, encode=False):
        headers = {
            'uid': str(self.user_id),
            'app_id': str(self.app_id),
            'app_key': self.app_key,
            'Content-type': 'application/x-www-form-urlencoded'
        }

        data = urllib.parse.urlencode(
            body) if encode and body is not None else body

        r = requests.request(
            method=method,
            url=url,
            data=data,
            headers=headers
        )

        r.raise_for_status()

        return r.json()

    def getPlants(self):
        url = f'{self.base_url}/plant/list'

        data = self._api_request(url, 'GET', None)
        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", f"plant list {data}")

        return data['data'].get('plants', [])

    def getPlantData(self, plant_id):

        url = f'{self.base_url}/plant/data?plant_id={plant_id}'

        rawdata = self._api_request(url, 'GET', None)
        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", f"plant data ({plant_id}) {rawdata}")
        data = rawdata['data']
        # Adjust power to Watt (not kW) and covert strings numbers to float or int
        data['total_energy'] = float(data['total_energy'])
        data['current_power'] = int(data['current_power'] * 1000)
        data['peak_power_actual'] = int(data['peak_power_actual'] * 1000)
        data['income'] = float(data['income'])
        data['last_update'] = datetime.timestamp(datetime.strptime(f"{data['last_update_time']} UTC+0000",
                                                 '%Y-%m-%dT%H:%M:%SZ %Z%z'))

        return data
