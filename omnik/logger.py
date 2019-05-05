import os
import sys
import logging
import re

import csv
import json

import requests
from requests.auth import HTTPBasicAuth

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger('omnik')

class DataLogger(object):
  def __init__(self, url, username, password):
    logger.debug('-> connecting to {}'.format(url))
    try:
      res = requests.get(url, auth=HTTPBasicAuth(username, password))
      res.raise_for_status()
      self.raw = res.text
    except requests.exceptions.HTTPError as e:
      logger.error('Unable to get data. [{0}]: {1}'.format(type(e).__name__, str(e)))
      raise e

  def transform(self, data):
    fieldnames = ('inverter_sn', 'fw_v_main', 'fw_v_slave', 'inverter_model', 'rated_power_w', 'current_power_w', 'yield_today_kwh', 'yield_total_kwh', 'alerts', 'last_updated', 'empty')
    reader = csv.DictReader(data, fieldnames)
    return json.loads(json.dumps(next(reader)))

  def process(self):
    try:
      match = re.search(r'^myDeviceArray\[0\]=.*;$', self.raw, re.MULTILINE)
      if not match:
        raise Exception('Invalid data')

      line = match.group(0)
      _json = self.transform(re.findall('"([^"]*)"', line))

      logger.debug(json.dumps(_json, indent=2))

    except Exception as e:
      logger.error('Oooops ... {0}: {1}'.format(type(e).__name__, str(e)))
      raise e
