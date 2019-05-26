import os
import sys
import logging

from .datalogger import DataLogger

logging.basicConfig(stream=sys.stdout, level=os.environ.get('LOGLEVEL', logging.INFO))

__version__ = '0.0.1'