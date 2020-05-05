import os
import sys
import logging
from ha_logger import hybridlogger

import datetime
from threading import Timer

logging.basicConfig(stream=sys.stdout,
                    level=os.environ.get('LOGLEVEL', logging.INFO))

__version__ = '1.1.0'

logger = logging.getLogger(__name__)

class RepeatedJob(object):
    def __init__(self, c, function, hass_api, *args, **kwargs):
        if c.get('default','debug', fallback=False):
            logger.setLevel(logging.DEBUG)
        self._timer = None
        self.logger = logger
        self.hass_api = hass_api
        self.interval = int(c.get('default','interval', fallback=360))
        self.half_interval = self.interval/2
        self.function = function
        self.args = args
        self.kwargs = kwargs
        #Try running for the first time
        self._run()

    # This handler function is fired when the timer has reached the interval
    def _run(self):
        self.is_running = False
        #The function calls DataLogger.process()
        self.last_update_time = self.function(*self.args, **self.kwargs)
        #Calculate the new timer interval
        if self.last_update_time :
            if self.last_update_time < datetime.datetime.now(datetime.timezone.utc):
                #if last report time + 2x interval is less than the current time then increase
                self.new_report_expected_at = self.last_update_time + datetime.timedelta(seconds=self.interval)
                #check if we have at least 60 seconds for the next cycle
                if (self.new_report_expected_at + datetime.timedelta(seconds=-10) < datetime.datetime.now(datetime.timezone.utc)):
                    #no recent update of missing update: wait {interval} from now()
                    self.new_report_expected_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=self.interval)
                # start timer - def start(self):
            else:
                #skipping dark period
                self.new_report_expected_at=self.last_update_time
            self.calculated_interval=(self.new_report_expected_at-datetime.datetime.now(datetime.timezone.utc)).seconds
        else:
            #and error occured retry in 2 minutes
            self.new_report_expected_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=self.half_interval)
            self.calculated_interval=(self.new_report_expected_at-datetime.datetime.now(datetime.timezone.utc)).seconds
        hybridlogger.ha_log(self.logger, self.hass_api, "INFO", f"new poll in {self.calculated_interval} seconds at {self.new_report_expected_at.isoformat()}.")
        self.start()

    # This function actual starts the timer
    def start(self):
        # starting actual timer
        if not self.is_running:
            self._timer = Timer(self.calculated_interval, self._run)
            self._timer.daemon = True
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False
