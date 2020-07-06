import requests
import urllib.parse
from omnik.ha_logger import hybridlogger
import hashlib
import xml.etree.ElementTree as ET
import datetime
from omnik.plugin_client import Client


class SolarmanPVClient(Client):

    def __init__(self):
        super().__init__()
        hybridlogger.ha_log(self.logger, self.hass_api, "INFO", "Client enabled: solarmanpvclient")

        # API Key
        self.api_key = self.config.get('client.solarmanpv', 'api_key', fallback='apitest')
        self.user_id = -1
        self.token = None

        self.base_url = self.config.get('client.solarmanpv', 'base_url',
                                        fallback='http://www.solarmanpv.com:18000/SolarmanApi/serverapi')

        self.username = self.config.get('client.solarmanpv', 'username')
        self.password = self.config.get('client.solarmanpv', 'password')

    def initialize(self):
        pwhash = hashlib.md5(self.password.encode('utf-8')).hexdigest()
        url = f'{self.base_url}/Login?username={self.username}&password={pwhash}&key={self.api_key}'

        xmldata = self._api_request(url, 'GET', None)
        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", f"account validation: {xmldata}")

        # Parsing the XML
        for element in ET.fromstring(xmldata):
            if element.tag == "userID":
                self.user_id = int(element.text)
            elif element.tag == "token":
                self.token = element.text

    def _api_request(self, url, method, body, encode=False):
        '''
        This API mithod uses XML. When logging in a token is obtained.
        For each request is to be checked if the token is still valid.
        '''
        headers = {
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

        return r.content

    def getPlants(self):

        data = []
        for plant in self.config.getlist('client.solarmanpv', 'plant_id_list'):
            data.append({'plant_id': plant})

        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", f"plant list from config {data}")

        return data

    def xmlprop(self, xml, params, fallback=None):
        paramlist = params
        param = paramlist.pop(0)
        for el in xml:
            if param == el.tag:
                if paramlist:
                    return self.xmlprop(el, paramlist, fallback)
                else:
                    return el.text
        return fallback

    def getPlantData(self, plant_id):

        data = {}
        url = f'{self.base_url}/Data?username={self.username}&stationid={plant_id}&key={self.api_key}&token={self.token}'

        xmldata = self._api_request(url, 'GET', None)
        hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", f"plant data ({plant_id}) {xmldata}")
        # Parsing the XML
        xml = ET.fromstring(xmldata)

        # Check if an error was returned
        if xml.tag != 'data':
            # log warning
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", "No valid data received. Trying to renew token.")
            # Get new token
            self.initialize()
            # Retry the call
            url = f'{self.base_url}/Data?username={self.username}&stationid={plant_id}&key={self.api_key}&token={self.token}'
            xmldata = self._api_request(url, 'GET', None)
            hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG", f"plant data retry ({plant_id}) {xmldata}")
            # Parsing the XML
            xml = ET.fromstring(xmldata)

        if xml.tag == 'data':
            data['name'] = self.xmlprop(xml, ['name'])
            data['income'] = float(self.xmlprop(xml, ['income', 'TotalIncome'], 0.0))
            data['data_logger'] = self.xmlprop(xml, ['detail', 'WiFi', 'id'], '')
            data['inverter'] = self.xmlprop(xml, ['detail', 'WiFi', 'inverter', 'SN'], '')
            data['status'] = int(self.xmlprop(xml, ['detail', 'WiFi', 'inverter', 'status'], 0))
            data['current_power'] = int(float(self.xmlprop(xml, ['detail', 'WiFi', 'inverter', 'power'], 0.0)) * 1000)
            data['today_energy'] = float(self.xmlprop(xml, ['detail', 'WiFi', 'inverter', 'etoday'], 0.0))
            data['total_energy'] = float(self.xmlprop(xml, ['detail', 'WiFi', 'inverter', 'etotal'], 0.0))
            data['last_update'] = float(self.xmlprop(xml, ['detail', 'WiFi', 'inverter', 'lastupdated'],
                                        datetime.datetime.now().timestamp()))
            data['last_update_time'] = datetime.datetime.utcfromtimestamp(data['last_update']).strftime('%Y-%m-%dT%H:%M:%SZ')
            return data
        else:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", f"Cannot fetch data: {xmldata}")
            return None
