import os
import sys
import logging

from .client import DataLoggerWifi, DataLoggerEth

logging.basicConfig(stream=sys.stdout, level=os.environ.get('LOGLEVEL', logging.INFO))

__version__ = '0.0.1'