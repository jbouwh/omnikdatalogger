import datetime
import tzlocal
import time
from astral import Astral

global default_timezone
global default_city_name

default_timezone = 'CET'
default_city_name = 'Amsterdam'

class daylight(object):
   def __init__(self,city_name=default_city_name, date=datetime.date.today()):
      self._a = Astral()
      self._a.solar_depression = 'civil'
      self._city = self._a[city_name]
      self.timezone = self._city.timezone
      self.sun = self._city.sun(date=date)
   @property
   def dawn(self):
      return self.sun['dawn']
   @property
   def sunrise(self):
      return self.sun['sunrise']
   @property
   def noon(self):
      return self.sun['noon']
   @property
   def sunset(self):
      return self.sun['sunset']
   @property
   def dusk(self):
      return self.sun['dusk']
   
   def sun_rising(self, time:datetime.datetime=datetime.datetime.now(tzlocal.get_localzone())):
      return (time > self.sun['dawn']) and (time < self.sun['sunrise'])
   
   def sun_up(self, time:datetime.datetime=datetime.datetime.now(tzlocal.get_localzone())):
      return (time > self.sun['sunrise']) and (time < self.sun['sunset'])

   def sun_setting(self, time:datetime.datetime=datetime.datetime.now(tzlocal.get_localzone())):
      return (time > self.sun['sunset']) and (time < self.sun['dusk'])

   def sun_down(self, time:datetime.datetime=datetime.datetime.now(tzlocal.get_localzone())):
      return (time < self.sun['dawn']) or (time > self.sun['dusk'])

def main():
   dl=daylight('Amsterdam')
   nu = datetime.datetime.now(tz=tzlocal.get_localzone())
   print('Now:     %s' % str(nu))
   print('Timezone:%s' % str(tzlocal.get_localzone()))
   print('Dawn:    %s' % str(dl.dawn))
   print('Sunrise: %s' % str(dl.sunrise))
   print('Noon:    %s' % str(dl.noon))
   print('Sunset:  %s' % str(dl.sunset))
   print('Dusk:    %s' % str(dl.dusk))
   print('dDawn:    %s' % str(dl.dawn-nu))
   print('dSunrise: %s' % str(dl.sunrise-nu))
   print('dNoon:    %s' % str(dl.noon-nu))
   print('dSunset:  %s' % str(dl.sunset-nu))
   print('dDusk:    %s' % str(dl.dusk-nu))
   print('Sun rising :', dl.sun_rising())
   print('Sun up     :', dl.sun_up())
   print('Sun setting:', dl.sun_setting())
   print('Sun down   :', dl.sun_down())
    
if __name__=="__main__":
   main()

