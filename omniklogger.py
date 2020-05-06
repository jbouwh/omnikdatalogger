#!/usr/bin/env python

import os
import argparse
import configparser
import time
import logging
from ha_logger import hybridlogger
import requests
import appdaemon.plugins.hass.hassapi as hass

logger = logging.getLogger(__name__)


from omnik import RepeatedJob
from omnik.datalogger import DataLogger

#customize config parser with dict based lookup for AppDaemon and command line options
#has_option and get function have been adapted
ha_args={}

class ha_ConfigParser(configparser.ConfigParser):
    def __init__(self, ha_args:dict=None, *args, **kwargs):
        if ha_args is None:
            self.ha_args={}
        else:
            self.ha_args=ha_args
        super().__init__(*args, **kwargs) 

    def has_option(self, section:str, option:str):
        if str.lower(section) == 'default':
            if option in self.ha_args:
                return True
        else:
            if section in self.ha_args:
                if option in self.ha_args[section]:
                    return True
        return super().has_option(section, option)

    def get(self, section:str, option:str, fallback=None, **kwargs):        
        if str.lower(section) == 'default':
            if option in self.ha_args:
                return self.ha_args.get(option, fallback)
        else:
            if str(section) in self.ha_args:
                if option in self.ha_args[section]:
                    return self.ha_args[section].get(option, fallback)
        try:
            retval=super().get(section, option, fallback=fallback, **kwargs)
        except:
            retval=fallback
        return retval

    def getboolean(self, section:str, option:str, fallback=None, **kwargs):
        try:
            retval = str(super().get(section, option, fallback=fallback, **kwargs)).lower() in ['true', '1', 't', 'y', 'yes', 'j', 'ja']
        except:
            retval = fallback
        return retval

    def getlist(self, section:str, option:str, fallback=[], **kwargs):
        if str.lower(section) == 'default':
            if option in self.ha_args:
                return self.ha_args.get(option, fallback)
        else:
            if str(section) in self.ha_args:
                if option in self.ha_args[section]:
                    return self.ha_args[section].get(option, fallback)
        try:
            retval = super().getlist(section, option, fallback=fallback, **kwargs)
        except:
            retval=fallback
            pass
        return retval



# TODO getboolean, getlist
# s.lower() in ['true', '1', 't', 'y', 'yes', 'j', 'ja']


# Initializaion class for AppDaemon (homeassistant)
class HA_OmnikDataLogger(hass.Hass): #hass.Hass


    def initialize(self, *args, **kwargs):
        hybridlogger.ha_log(logger, self, "INFO", f"Starting Omnik datalogger...")
        hybridlogger.ha_log(logger, self, "DEBUG", f"Arguments from AppDaemon config (self.args): {self.args}")
        if 'config' in self.args:
            c = ha_ConfigParser(converters={'list': lambda x: [i.strip() for i in x.split(',')]}, ha_args=self.args)
            self.configfile=self.args['config']
            try:
                c.read(self.configfile, encoding='utf-8')
                hybridlogger.ha_log(logger, self, "INFO", f"Using configuration from '{self.configfile}'.")
            except Exception as e:
                hybridlogger.ha_log(logger, self, "ERROR", f"Error reading 'config.ini' from {self.configfile}. No valid configuration file. {e}.")
        else:
            c = ha_ConfigParser(ha_args=self.args)

        self.interval=int(c.get('default', 'interval', 360))
        self.clazz = DataLogger(c, hass_api=self)
        # running repeatedly, every X seconds
        hybridlogger.ha_log(logger, self, "INFO", f"Daemon interval {self.interval} seconds.")
          
        self.rt = RepeatedJob(c, function=self.clazz.process, hass_api=self)

    def terminate(self):
        hybridlogger.ha_log(logger, self, "INFO", f"Daemon was stopped.")
        self.rt.stop()

# Initialisation form commandline
def main(c:ha_ConfigParser, hass_api=None):
    if c.get('default','debug', False): 
        logger.setLevel(logging.DEBUG)
    clazz = DataLogger(c, hass_api=hass_api)
    if c.has_option('default','interval'):
        # running repeatedly, every X seconds
        hybridlogger.ha_log(logger, hass_api, "INFO", f"Monitoring interval {c.get('default','interval')} seconds.")
          
        rt = RepeatedJob(c, function=clazz.process, hass_api=hass_api)
        if hass_api:
            hass_api.rt = rt
        else:
            # loop is only for commandline execution
            try:
                while True:
                    # FIXME: add check for kill switch ... this does _not_ work
                    # if 'OMNIK_KILL_SWITCH' in os.environ:
                    #   print('> found kill switch: stopping all threads')
                    #   rt.stop()
                    #   os.sys.exit(1)
                    time.sleep(0.5)
            except KeyboardInterrupt:
                hybridlogger.ha_log(logger, hass_api, "INFO", '> stopping all threads')
                rt.stop()    
    else:
        # running only once
        clazz.process()

if __name__ == '__main__':
    home   = os.path.expanduser('~')
    parser = argparse.ArgumentParser()
  
    parser.add_argument('--config', default=os.path.join(home, '.omnik/config.ini'), help='Path to configuration file', metavar="FILE")
    parser.add_argument('--interval', type=int, help='Execute every n seconds')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode')

    args = parser.parse_args()

    if not os.path.isfile(args.config):
        print("Unable to find config at '{}'".format(args.config))
        parser.print_help()
        os.sys.exit(1)
    if args.config:
        ha_args['config']=args.config
        if args.debug:
            ha_args['debug']=args.debug
        if args.interval:
            ha_args['interval']=args.interval
        c = ha_ConfigParser(converters={'list': lambda x: [i.strip() for i in x.split(',')]}, ha_args=ha_args)
        c.read([args.config], encoding='utf-8')

    main(c, hass_api=None)
