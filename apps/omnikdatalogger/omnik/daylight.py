import datetime
import pytz
from astral import Astral

global default_timezone
global default_city_name

default_timezone = 'CET'
default_city_name = 'Amsterdam'


class daylight(object):

    def __init__(self, city_name=default_city_name):
        self._a = Astral()
        self._a.solar_depression = 'civil'
        self._city = self._a[city_name]
        self._timezone = pytz.timezone(self._city.timezone)

    @property
    def dawn(self, date=None):
        if not date:
            date = datetime.datetime.now(self.timezone)
        self.sun = self._city.sun(date=date)
        return self.sun['dawn']

    @property
    def next_dawn(self, date=None):
        if not date:
            date = datetime.datetime.now(self.timezone)
        self.sun = self._city.sun(date=date)
        if (self.sun['dawn'] < date):
            self.sun = self._city.sun(date=date+datetime.timedelta(days=1))
        return self.sun['dawn']

    @property
    def sunrise(self, date=None):
        if not date:
            date = datetime.datetime.now(self.timezone)
        self.sun = self._city.sun(date=date)
        return self.sun['sunrise']

    @property
    def noon(self, date=None):
        self.sun = self._city.sun(date=date)
        return self.sun['noon']

    @property
    def sunset(self, date=None):
        if not date:
            date = datetime.datetime.now(self.timezone)
        self.sun = self._city.sun(date=date)
        return self.sun['sunset']

    @property
    def dusk(self, date=None):
        if not date:
            date = datetime.datetime.now(self.timezone)
        self.sun = self._city.sun(date=date)
        return self.sun['dusk']

    @property
    def timezone(self):
        return self._timezone

    def sun_rising(self, time: datetime.datetime = None):
        if not time:
            time = datetime.datetime.now(self.timezone)
        self.sun = self._city.sun(date=time)
        return (time > self.sun['dawn']) and (time < self.sun['sunrise'])

    def sun_up(self, time: datetime.datetime = None):
        if not time:
            time = datetime.datetime.now(self.timezone)
        self.sun = self._city.sun(date=time)
        return (time > self.sun['sunrise']) and (time < self.sun['sunset'])

    def sun_shine(self, time: datetime.datetime = None):
        if not time:
            time = datetime.datetime.now(self.timezone)
        self.sun = self._city.sun(date=time)
        return (time > self.sun['dawn']) and (time < self.sun['dusk'])

    def sun_setting(self, time: datetime.datetime = None):
        if not time:
            time = datetime.datetime.now(self.timezone)
        self.sun = self._city.sun(date=time)
        return (time > self.sun['sunset']) and (time < self.sun['dusk'])

    def sun_down(self, time: datetime.datetime = None):
        if not time:
            time = datetime.datetime.now(self.timezone)
        self.sun = self._city.sun(date=time)
        return (time < self.sun['dawn']) or (time > self.sun['dusk'])


def main():
    dl = daylight('Amsterdam')
    nu = datetime.datetime.now(tz=dl.timezone)
    print('Now:     %s' % str(nu))
    print('Timezone:%s' % str(dl.timezone))
    print('Dawn:    %s' % str(dl.dawn))
    print('nxtdawn: %s' % str(dl.next_dawn))
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
    print('Sun shine  :', dl.sun_shine())
    print('Sun setting:', dl.sun_setting())
    print('Sun down   :', dl.sun_down())


if __name__ == "__main__":
    main()
