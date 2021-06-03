from datetime import datetime, timedelta
import pytz

try:
    from astral import sun
    from astral.geocoder import database, lookup

    VERSION = 2
except ImportError:
    from astral import Astral

    VERSION = 1

global default_city_name

default_city_name = "Amsterdam"


class daylight(object):
    def __init__(self, city_name=default_city_name):
        if VERSION == 2:
            self._city = lookup("Amsterdam", database())
            self._sun = self.sun(datetime.now())
        else:
            self._a = Astral()
            self._a.solar_depression = "civil"
            self._city = self._a[city_name]
            self._timezone = pytz.timezone(self._city.timezone)

    def sun(self, t=None):
        if not t:
            t = self.localtime()
        if VERSION == 2:
            return sun.sun(self._city.observer, t, tzinfo=self._city.timezone)
        else:
            return self._city.sun(t)

    def localtime(self, t=None):
        if not t:
            t = datetime.now()
        return self._city.tzinfo.localize(t)

    @property
    def version(self):
        return VERSION

    @property
    def dawn(self):
        return self.sun()["dawn"]

    @property
    def next_dawn(self):
        _sundawn = self.dawn
        if _sundawn < self.localtime():
            _sundawn = self.sun(self.localtime() + timedelta(days=1))["dawn"]
        return _sundawn

    @property
    def sunrise(self):
        return self.sun()["sunrise"]

    @property
    def noon(self):
        return self.sun()["noon"]

    @property
    def sunset(self):
        return self.sun()["sunset"]

    @property
    def dusk(self):
        return self.sun()["dusk"]

    def sun_rising(self, time: datetime = None):
        if not time:
            time = self.localtime()
        _sun = self.sun(time)
        return (time > _sun["dawn"]) and (time < _sun["sunrise"])

    def sun_up(self, time: datetime = None):
        if not time:
            time = self.localtime()
        _sun = self.sun(time)
        return (time > _sun["sunrise"]) and (time < _sun["sunset"])

    def sun_shine(self, time: datetime = None):
        if not time:
            time = self.localtime()
        _sun = self.sun(time)
        return (time > _sun["dawn"]) and (time < _sun["dusk"])

    def sun_setting(self, time: datetime = None):
        if not time:
            time = self.localtime()
        _sun = self.sun(time)
        return (time > _sun["sunset"]) and (time < _sun["dusk"])

    def sun_down(self, time: datetime = None):
        if not time:
            time = self.localtime()
        _sun = self.sun(time)
        return (time < _sun["dawn"]) or (time > _sun["dusk"])


def main():
    dl = daylight("Amsterdam")
    nu = dl.localtime()
    print("Version: %s" % str(dl.version))
    print("Now:     %s" % str(nu))
    print("Dawn:    %s" % str(dl.dawn))
    print("nxtdawn: %s" % str(dl.next_dawn))
    print("Sunrise: %s" % str(dl.sunrise))
    print("Noon:    %s" % str(dl.noon))
    print("Sunset:  %s" % str(dl.sunset))
    print("Dusk:    %s" % str(dl.dusk))
    print("dDawn:    %s" % str(dl.dawn - nu))
    print("dSunrise: %s" % str(dl.sunrise - nu))
    print("dNoon:    %s" % str(dl.noon - nu))
    print("dSunset:  %s" % str(dl.sunset - nu))
    print("dDusk:    %s" % str(dl.dusk - nu))
    print("Sun rising :", dl.sun_rising())
    print("Sun up     :", dl.sun_up())
    print("Sun shine  :", dl.sun_shine())
    print("Sun setting:", dl.sun_setting())
    print("Sun down   :", dl.sun_down())


if __name__ == "__main__":
    main()
