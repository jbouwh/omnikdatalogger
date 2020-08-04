import os
import sys
import logging
from omnik.ha_logger import hybridlogger

from datetime import datetime, timedelta, timezone
import threading

logging.basicConfig(stream=sys.stdout,
                    level=os.environ.get('LOGLEVEL', logging.INFO))

__version__ = '1.2.15'

logger = logging.getLogger(__name__)


class RepeatedJob(object):
    def __init__(self, c, datalogger, hass_api, *args, **kwargs):
        if c.get('default', 'debug', fallback=False):
            logger.setLevel(logging.DEBUG)
        self.logger = logger
        self.hass_api = hass_api
        self.datalogger = datalogger
        self.client = datalogger.client
        self.use_timer = datalogger.client.use_timer
        if self.use_timer:
            self._timer = None
            self.interval = int(c.get('default', 'interval', fallback=360))
            self.half_interval = self.interval/2
            self.retries = 0
            # Trigger the RepeatedJob using a short timer (1s) for the first time so the initialization can finish
            self.calculated_interval = 1
        else:
            self.semaphore = self.client.semaphore
            self.msgevent = self.client.msgevent
        self.args = args
        self.kwargs = kwargs
        # Initialize retry counter
        self.is_running = False
        self.start()

    def function_thread(self):
        return self.function_thread

    # This handler function is fired when the timer has reached the interval
    def _run(self):
        self.is_running = False
        # The function calls DataLogger.process()
        self.last_update_time = self.datalogger.process(*self.args, **self.kwargs)
        # Calculate the new timer interval
        if self.last_update_time:
            # Reset retry counter
            self.retries = 0
            if self.last_update_time <= datetime.now(timezone.utc):
                # If last report time + 2x interval is less than the current time then increase
                self.new_report_expected_at = self.last_update_time + timedelta(seconds=self.interval)
                # Check if we have at least 60 seconds for the next cycle
                if (self.new_report_expected_at + timedelta(seconds=-10) <
                        datetime.now(timezone.utc)):
                    # No recent update of missing update: wait {interval} from now()
                    self.new_report_expected_at = datetime.now(timezone.utc) + \
                        timedelta(seconds=self.interval)
            else:
                # Skipping dark period
                self.new_report_expected_at = self.last_update_time
            self.calculated_interval = (self.new_report_expected_at - datetime.now(timezone.utc)).seconds
        else:
            # An error occured calculate retry interval
            retry_interval = self.half_interval
            i = self.retries
            while i > 0:
                # Double retry interval to avoid to much traffic
                retry_interval *= 2
                i -= 1
            # Increment retry counter maximal interval between retries is half_interval * 2 * 2 * 2 = 4 intervals
            if self.retries < 3:
                self.retries += 1
            # Calculate new report time
            self.new_report_expected_at = datetime.now(timezone.utc) + \
                timedelta(seconds=retry_interval)
            self.calculated_interval = (self.new_report_expected_at - datetime.now(timezone.utc)).seconds
        # Make sure we have at least 15 seconds on the time to prevent a deadlocked timer loop
        if self.calculated_interval < 15:
            self.calculated_interval = 15
        hybridlogger.ha_log(self.logger, self.hass_api, "INFO",
                            f"new poll in {self.calculated_interval} seconds at {self.new_report_expected_at.isoformat()}.")
        self.start()

    # This function actual starts the timer
    def start(self):
        if self.use_timer:
            # starting actual timer
            if not self.is_running:
                self._timer = threading.Timer(self.calculated_interval, self._run)
                self._timer.daemon = True
                self._timer.start()
                self.is_running = True
        else:
            # use a listing thread to process
            self.listenthread = threading.Thread(target=self._listen_to_events)
            self.listenthread.start()

    def stop(self):
        if self.use_timer:
            self._timer.cancel()
        else:
            # exit event message loop
            self.msgevent.set()
        self.is_running = False

    def _listen_to_events(self):
        self.is_running = True
        while self.is_running:
            self.last_update_time = self.datalogger.process(*self.args, **self.kwargs)
