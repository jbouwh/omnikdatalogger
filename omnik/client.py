import logging
import json

import requests
import urllib.parse

class OmnikPortalClient(object):

  def _api_request(self, url, method, body, encode=False):
    headers = {
      'uid': str(self.user_id),
      'app_id': str(self.app_id),
      'app_key': self.app_key,
      'Content-type': 'application/x-www-form-urlencoded'
    }

    data = urllib.parse.urlencode(body) if encode and body is not None else body

    r = requests.request(
      method=method, 
      url=url, 
      data=data, 
      headers=headers
    )

    r.raise_for_status()

    return r.json()

  def __init__(self, logger, username, password):
    self.logger   = logger
    self.app_id   = 10038
    self.app_key  = 'Ox7yu3Eivicheinguth9ef9kohngo9oo'
    self.user_id  = -1

    self.base_url = 'https://api.omnikportal.com/v1'

    self.username = username
    self.password = password

  def initialize(self):
    url = '{0}/user/account_validate'.format(self.base_url)    

    body = {
      'user_email': self.username,
      'user_password': self.password,
      'user_type': 1
    }

    data = self._api_request(url, 'POST', body)    

    # this is what `initialize` does ... setting the `user_id`
    self.user_id = data['data']['c_user_id']

  def getPlants(self):
    url = '{0}/plant/list'.format(self.base_url)

    data = self._api_request(url, 'GET', None)

    return data['data'].get('plants', [])


  def getPlantData(self, plant_id):
    url = '{0}/plant/data?plant_id={1}'.format(self.base_url, plant_id)

    data = self._api_request(url, 'GET', None)

    return data['data']