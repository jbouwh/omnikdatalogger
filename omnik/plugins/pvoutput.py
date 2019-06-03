import json
from datetime import datetime

from cachetools import TTLCache
import requests
from omnik.plugins import CachedPlugin

class PVOutput(CachedPlugin):

  def get_weather(self):
    try:
      if 'weather' not in self.cache:
        self.logger.info('[CACHE MISS] Weather data _not_ in cache ... fetching now')
        url = "https://{endpoint}/data/2.5/weather?lon={lon}&lat={lat}&units={units}&APPID={api_key}".format(
          endpoint = self.config.get('openweathermap', 'endpoint'),
          lat      = self.config.get('openweathermap', 'lat'),
          lon      = self.config.get('openweathermap', 'lon'),
          units    = self.config.get('openweathermap', 'units', fallback='metric'),
          api_key  = self.config.get('openweathermap', 'api_key'),
        )

        res = requests.get(url)

        self.logger.debug('OK') if res.status_code == 200 else self.logger.debug('NOK: {}'.format(res.status_code))

        res.raise_for_status()

        self.cache['weather'] = res.json()
      else:
        self.logger.info('[CACHE HIT] Got cached weather data')

      return self.cache['weather']

    except requests.exceptions.HTTPError as e:
      self.logger.error('Unable to get data. [{0}]: {1}'.format(type(e).__name__, str(e)))
      raise e

  def process_message(self, **args):
    """
    Send data to pvoutput
    """
    try:
	    now = datetime.utcnow()
	
	    self.logger.info('Uploading to PVOutput')
	
	    msg = args['msg']
	
	    _json = json.dumps(msg, indent=2)
	
	    self.logger.info('> Processing message: {}'.format(_json))
	
	    # See: https://pvoutput.org/help.html
	
	    # v3 = Energy Consumed
	    # v4 = Power Consumed
	    # v6 = Voltage
	    # c1 = Cumulative (0/1)
	    # n = Net Flag (0/1)
	
	    data = {
	        'key': self.config.get('pvoutput', 'api_key'),
	        'sid': self.config.get('pvoutput', 'sys_id'),
	        'd': now.strftime('%Y%m%d'),
	        't': now.strftime('%H:%M'),
	        'v1': msg['i_eall'],
	        'v2': float(msg['i_eday']) * 100
	    }
	
	    if self.config.getboolean('pvoutput', 'use_temperature', fallback=False):
	      weather = self.get_weather()
	
	      self.logger.info('> got {}'.format(json.dumps(weather, indent=2)))
	
	      data['v5'] = str(weather['main']['temp'])
	  
	    url = "http://pvoutput.org/service/r2/addstatus.jsp"
	
	    self.logger.info(json.dumps(data, indent=2))

	except Exception as e:
		self.logger.error(e, exc_info=True)
    

    