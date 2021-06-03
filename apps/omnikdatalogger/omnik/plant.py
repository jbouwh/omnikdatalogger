from datetime import datetime, timezone, time
from decimal import Decimal


class Plant:
    def __init__(self, plant_id=None, last_update_time=None, *args, **kwargs):
        self._plant_id = plant_id
        self._last_update_time = (
            last_update_time if last_update_time else datetime.now(timezone.utc)
        )
        self._updated = bool(last_update_time)
        self._data = None

    def plant_id(self):
        return self._plant_id

    def pop_for_aggregate(self, cache):
        data_age = (datetime.now(timezone.utc) - self._last_update_time).seconds
        if data_age > 360:
            # data is too old discard, use cache
            self._updated = False
            # return True to ensure publising
            if not self._data:
                self._data = {}
            try:
                self._data["total_energy"] = cache[
                    f"{self._plant_id}.last_total_energy"
                ]
                self._data["today_energy"] = cache[
                    f"{self._plant_id}.last_today_energy"
                ]
                self._data["current_power"] = Decimal("0.0")
                self._data["last_update"] = time.time()
            except:
                return False
            return True
        if self._updated:
            self._updated = False
            return True
        else:
            # Data still valid, wait until all inverters showed their data
            return False

    @property
    def last_update_time(self):
        return self._last_update_time

    @last_update_time.setter
    def last_update_time(self, last_update_time):
        self._last_update_time = last_update_time
        self._updated = True

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data
        self._updated = True
