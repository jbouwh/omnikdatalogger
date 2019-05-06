import os
import sys
import logging
import re

import csv
import json

import requests
from requests.auth import HTTPBasicAuth

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger('omnik')

class DataLogger(object):
  def __init__(self, url, username, password, debug):
    if debug:
      logger.setLevel(logging.DEBUG)

    logger.debug('-> Connecting to {}'.format(url))
    try:
      res = requests.get(url, auth=HTTPBasicAuth(username, password))

      logger.debug('OK') if res.status_code == 200 else logger.debug('NOK: {}'.format(res.status_code))

      res.raise_for_status()
      self.raw = res.text
    except requests.exceptions.HTTPError as e:
      logger.error('Unable to get data. [{0}]: {1}'.format(type(e).__name__, str(e)))
      raise e

  def transform(self, data):
    fieldnames = ('inverter_sn', 'fw_v_main', 'fw_v_slave', 'inverter_model', 'rated_power_w', 'current_power_w', 'yield_today_kwh', 'yield_total_kwh', 'alerts', 'last_updated', 'empty')
    reader = csv.DictReader(data, fieldnames)
    return json.loads(json.dumps(next(reader)))

  def correct(self, data):
    """
    Correct values to reflect used uom (~ unit of measure)
    """
    corr = {
      'yield_today_kwh': 100,
      'yield_total_kwh': 10
    }
    for k in corr.keys():
      if k in data:
        data[k] = int(data[k]) / corr[k]
    return data

  def process(self, args):
    try:
      match = re.search(r'^myDeviceArray\[0\]=.*;$', self.raw, re.MULTILINE)
      if not match:
        raise Exception('Invalid data')

      line = match.group(0)
      _json = self.correct(self.transform(re.findall('"([^"]*)"', line)))

      # trigger plugins here
      # for plugin in plugins:
      #   plugin.process_message(_json)

      logger.info(json.dumps(_json, indent=2))

    except Exception as e:
      logger.error('Oooops ... {0}: {1}'.format(type(e).__name__, str(e)))
      raise e
