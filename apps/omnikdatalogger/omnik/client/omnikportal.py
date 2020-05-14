import requests
import urllib.parse
from ha_logger import hybridlogger


class OmnikPortalClient(Client):

    def __init__(self):
        super().__init__()
        hybridlogger.ha_log(self.logger, self.hass_api, "INFO", f"Client enabled: omnikportalclient")

        # API Key's
        self.app_id = self.config.get('omnikportal', 'app_id', fallback='10038')
        self.app_key = self.config.get('omnikportal', 'app_key', fallback='Ox7yu3Eivicheinguth9ef9kohngo9oo')
        self.user_id = -1

        self.base_url = self.config.get('omnikportal', 'base_url', fallback='https://api.omnikportal.com/v1')

        self.username = self.config.get('omnikportal', 'username')
        self.password = self.config.get('omnikportal', 'password')

    def initialize(self, logger):
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

    def getPlants(self, logger):
        url = f'{self.base_url}/plant/list'

        data = self._api_request(url, 'GET', None)
        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", f"plant list {data}")

        return data['data'].get('plants', [])

    def getPlantData(self, logger, plant_id):

        url = f'{self.base_url}/plant/data?plant_id={plant_id}'

        data = self._api_request(url, 'GET', None)
        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", f"plant data ({plant_id}) {data}")

        return data['data']