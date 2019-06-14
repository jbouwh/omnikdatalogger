import os
import sys
import logging
import time
from threading import Timer

from .datalogger import DataLogger

logging.basicConfig(stream=sys.stdout, level=os.environ.get('LOGLEVEL', logging.INFO))

__version__ = '0.0.3'

class RepeatedJob(object):
  def __init__(self, interval, function, *args, **kwargs):
    self._timer     = None
    self.interval   = interval
    self.function   = function  
    self.args       = args
    self.kwargs     = kwargs
    self.is_running = False
    self.start()

  def _run(self):
    self.is_running = False
    self.start()
    self.function(*self.args, **self.kwargs)

  def start(self):
    if not self.is_running:
      self._timer = Timer(self.interval, self._run)
      self._timer.daemon = True
      self._timer.start()
      self.is_running = True

  def stop(self):
    self._timer.cancel()
    self.is_running = False