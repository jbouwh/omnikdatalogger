#! /usr/bin/env python3

import os
import argparse
import configparser
import pathlib
import time
import logging
import appdaemon.plugins.hass.hassapi as hass
from omnik.ha_logger import hybridlogger
from omnik import RepeatedJob
from omnik.datalogger import DataLogger

logger = logging.getLogger(__name__)

# customize config parser with dict based lookup for AppDaemon and command line options
# has_option and get function have been adapted
ha_args = {}


class ha_ConfigParser(configparser.ConfigParser):

    def __init__(self, ha_args: dict = None, *args, **kwargs):
        if ha_args is None:
            self.ha_args = {}
        else:
            self.ha_args = ha_args
        super().__init__(*args, **kwargs)

    def has_option(self, section: str, option: str):
        if str(section).lower() == 'default':
            if option in self.ha_args:
                return True
        else:
            if section in self.ha_args:
                if option in self.ha_args[section]:
                    return True
        return super().has_option(section, option)

    def get(self, section, option, fallback=None, **kwargs):
        if str(section).lower() == 'default':
            if option in self.ha_args:
                return self.ha_args.get(option, fallback)
        else:
            if str(section) in self.ha_args:
                if option in self.ha_args[section]:
                    return self.ha_args[section].get(option, fallback)
        try:
            if fallback:
                retval = super().get(section, option, fallback=fallback, **kwargs)
            else:
                retval = super().get(section, option, fallback='', **kwargs)
        except Exception:
            retval = fallback
        return retval

    def getboolean(self, section, option, fallback=None, **kwargs):
        truelist = ['true', '1', 't', 'y', 'yes', 'j', 'ja']
        valstr = str(self.get(section, option, fallback, **kwargs)).lower()
        return (valstr in truelist)

    def getlist(self, section, option, fallback=[], **kwargs):
        if str(section).lower() == 'default':
            if option in self.ha_args:
                return self.ha_args.get(option, fallback)
        else:
            if str(section) in self.ha_args:
                if option in self.ha_args[section]:
                    return self.ha_args[section].get(option, fallback)
        try:
            retval = super().getlist(section, option, fallback=fallback, **kwargs)
        except Exception:
            retval = fallback
            pass
        return retval


# Initialization class for AppDaemon (homeassistant)
class HA_OmnikDataLogger(hass.Hass):

    def initialize(self, *args, **kwargs):
        hybridlogger.ha_log(logger, self, "INFO", "Starting Omnik datalogger...")
        hybridlogger.ha_log(logger, self, "DEBUG", f"Arguments from AppDaemon config (self.args): {self.args}")
        if 'config' in self.args:
            c = ha_ConfigParser(converters={'list': lambda x: [i.strip() for i in x.split(',')]}, ha_args=self.args)
            self.configfile = self.args['config']
            try:
                c.read(self.configfile, encoding='utf-8')
                c.configfile = self.configfile
            except Exception as e:
                hybridlogger.ha_log(logger, self, "ERROR",
                                    f"Error parsing 'config.ini' from {self.configfile}. No valid configuration file. {e}.")
                c.configfile = None
        else:
            c = ha_ConfigParser(ha_args=self.args)
            c.configfile = None
        set_data_config_path(c)

        self.interval = int(c.get('default', 'interval', 360))
        self.datalogger = DataLogger(c, hass_api=self)

        # running repeatedly
        if self.datalogger.client.use_timer:
            hybridlogger.ha_log(logger, self, "INFO", f"Daemon interval {self.interval} seconds.")
        else:
            hybridlogger.ha_log(logger, self, "INFO", "Daemon starts listening.")
        self.rt = RepeatedJob(c, self.datalogger, hass_api=self)

    def terminate(self):
        self.datalogger.terminate()
        hybridlogger.ha_log(logger, self, "INFO", "DSMR Daemon was stopped.")
        self.rt.stop()
        hybridlogger.ha_log(logger, self, "INFO", "Daemon was stopped.")


# Initialization from the commandline
def main(c: ha_ConfigParser, hass_api=None):
    # Enabled debugging if the flag is set
    if c.get('default', 'debug', False):
        logger.setLevel(logging.DEBUG)
    set_data_config_path(c)
    datalogger = DataLogger(c, hass_api=hass_api)
    if c.has_option('default', 'interval'):
        # running repeatedly
        if datalogger.client.use_timer:
            hybridlogger.ha_log(logger, hass_api, "INFO", f"Daemon interval {int(c.get('default', 'interval', 360))} seconds.")
        else:
            hybridlogger.ha_log(logger, hass_api, "INFO", "Daemon starts listening.")
        rt = RepeatedJob(c, datalogger, hass_api)
        if hass_api:
            hass_api.rt = rt
        else:
            # loop is for commandline execution only
            try:
                while True:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                hybridlogger.ha_log(logger, hass_api, "INFO", '> stopping all threads')
                rt.stop()
                datalogger.terminate()

    else:
        # running only once
        datalogger.process()
        datalogger.terminate()


def set_data_config_path(config):
    config.data_config_file_path = f"{pathlib.Path(__file__).parent.absolute()}/data_fields.json"
    config.data_config_file_shared = f"{pathlib.Path(__file__).parent.parent.absolute()}" \
                                     "/share/omnikdatalogger/data_fields.json"


if __name__ == '__main__':
    home = os.path.expanduser('~')
    parser = argparse.ArgumentParser()

    parser.add_argument('--config', default=os.path.join(home, '.omnik/config.ini'),
                        help='Path to configuration file', metavar="FILE")
    parser.add_argument('--interval', type=int, help='Execute every n seconds')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode')

    args = parser.parse_args()

    if not os.path.isfile(args.config):
        logging.critical("Unable to find config at '{}'".format(args.config))
        parser.print_help()
        os.sys.exit(1)
    if args.config:
        ha_args['config'] = args.config
        if args.debug:
            ha_args['debug'] = args.debug
        if args.interval:
            ha_args['interval'] = args.interval
        c = ha_ConfigParser(converters={'list': lambda x: [i.strip() for i in x.split(',')]}, ha_args=ha_args)
        c.read([args.config], encoding='utf-8')
        c.configfile = args.config

    main(c, hass_api=None)
