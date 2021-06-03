#! /usr/bin/env python3

import os
import signal
import argparse
import configparser
import pathlib
import time
import logging
import yaml
from omnik.ha_logger import hybridlogger
from omnik import RepeatedJob
from omnik.datalogger import DataLogger

try:
    # AppDeamon is only needed when run used with AppDaemon
    import appdaemon.plugins.hass.hassapi as hass  # type: ignore
except ImportError:
    # AppDeamon is not needed when run in command mode uses dummy class
    class hass(object):
        Hass = object


logger = logging.getLogger(__name__)

# customize config parser with dict based lookup for AppDaemon and command line options
# has_option and get function have been adapted
ha_args = {}

global stopflag


# Generic signal handler
def signal_handler(signal, frame):
    global stopflag
    logging.debug("Signal {:0d} received. Setting stopflag.".format(signal))
    stopflag = True


class ha_ConfigParser(configparser.ConfigParser):
    def __init__(self, ha_args: dict = None, *args, **kwargs):
        if ha_args is None:
            self.ha_args = {}
        else:
            self.ha_args = ha_args
        super().__init__(*args, **kwargs)

    def has_option(self, section: str, option: str):
        if str(section).lower() == "default":
            if option in self.ha_args:
                return True
        else:
            if section in self.ha_args:
                if option in self.ha_args[section]:
                    return True
        return super().has_option(section, option)

    def get(self, section, option, fallback=None, **kwargs):
        if str(section).lower() == "default":
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
                retval = super().get(section, option, fallback="", **kwargs)
        except Exception:
            retval = fallback
        return retval

    def getboolean(self, section, option, fallback=None, **kwargs):
        truelist = ["true", "1", "t", "y", "yes", "j", "ja"]
        valstr = str(self.get(section, option, fallback, **kwargs)).lower()
        return valstr in truelist

    def getlist(self, section, option, fallback=[], **kwargs):
        if str(section).lower() == "default":
            if option in self.ha_args:
                return self.ha_args.get(option, fallback)
        else:
            if str(section) in self.ha_args:
                if option in self.ha_args[section]:
                    return self.ha_args[section].get(option, fallback)
        try:
            retval = super().get(section, option, fallback=fallback, **kwargs)
        except Exception:
            retval = fallback
            pass
        return retval


# Initialization class for AppDaemon (homeassistant)
class HA_OmnikDataLogger(hass.Hass):
    def initialize(self, *args, **kwargs):
        hybridlogger.ha_log(logger, self, "INFO", "Starting Omnik datalogger...")
        hybridlogger.ha_log(
            logger,
            self,
            "DEBUG",
            f"Arguments from AppDaemon config (self.args): {self.args}",
        )
        if "config" in self.args:
            c = ha_ConfigParser(
                converters={"list": lambda x: [i.strip() for i in x.split(",")]},
                ha_args=self.args,
            )
            self.configfile = self.args["config"]
            try:
                c.read(self.configfile, encoding="utf-8")
                c.configfile = self.configfile
            except Exception as e:
                hybridlogger.ha_log(
                    logger,
                    self,
                    "ERROR",
                    f"Error parsing config.ini '{self.configfile}'. No valid configuration file. {e}.",
                )
                c.configfile = None
        else:
            c = ha_ConfigParser(ha_args=self.args)
            c.configfile = None
        set_data_config_path(c)

        self.interval = int(c.get("default", "interval", 360))
        self.datalogger = DataLogger(c, hass_api=self)

        # running repeatedly
        if self.datalogger.client.use_timer:
            hybridlogger.ha_log(
                logger, self, "INFO", f"Daemon interval {self.interval} seconds."
            )
        else:
            hybridlogger.ha_log(logger, self, "INFO", "Daemon starts listening.")
        self.rt = RepeatedJob(c, self.datalogger, hass_api=self)

    def terminate(self):
        hybridlogger.ha_log(logger, self, "INFO", "Stopping Omnikdatalogger...")
        self.rt.stop()
        self.datalogger.terminate()
        hybridlogger.ha_log(logger, self, "INFO", "Omnikdatalogger was stopped")


# Initialization from the commandline
def main(c: ha_ConfigParser, hass_api=None):
    global stopflag
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    # Enabled debugging if the flag is set
    if c.get("default", "debug", False):
        logger.setLevel(logging.DEBUG)

    set_data_config_path(c)
    datalogger = DataLogger(c, hass_api=hass_api)
    if c.has_option("default", "interval"):
        # running repeatedly
        if datalogger.client.use_timer:
            hybridlogger.ha_log(
                logger,
                hass_api,
                "INFO",
                f"Daemon interval {int(c.get('default', 'interval', 360))} seconds.",
            )
        else:
            hybridlogger.ha_log(logger, hass_api, "INFO", "Daemon starts listening.")
        rt = RepeatedJob(c, datalogger, hass_api)
        if hass_api:
            hass_api.rt = rt
        else:
            # loop is for commandline execution only
            try:
                while not stopflag:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                pass
            hybridlogger.ha_log(logger, hass_api, "INFO", "Stopping Omnikdatalogger...")
            rt.stop()
            datalogger.terminate()
            hybridlogger.ha_log(logger, hass_api, "INFO", "Omnikdatalogger was stopped")

    else:
        # running only once
        datalogger.process()
        datalogger.terminate()


def set_data_config_path(config):
    config.data_config_file_path = (
        f"{pathlib.Path(__file__).parent.absolute()}/data_fields.json"
    )
    config.data_config_file_shared = (
        f"{pathlib.Path(__file__).parent.parent.absolute()}"
        "/share/omnikdatalogger/data_fields.json"
    )
    config.data_config_file_cwd = f"{os.getcwd()}/data_fields.json"


def get_yaml_settings(args):
    with open(args.settings, "r") as stream:
        try:
            settings = yaml.safe_load(stream)
            if args.section in settings:
                index = args.section
            else:
                for key in settings:
                    index = key
                    break
            logging.info(
                "Using section '{1}' from config file '{0}'".format(
                    args.settings, index
                )
            )
            return settings[index]
        except yaml.YAMLError as exc:
            logging.error(
                "YAML config file '{0}' could not be parsed. Error: {1}".format(
                    args.settings, exc
                )
            )
            os.sys.exit(1)


def setup_config_parser(args, settings):
    if not settings:
        logging.error("Config files '{0}' has no valid index".format(args.settings))
        os.sys.exit(1)
    elif "config" in settings:
        try:
            configfile = settings["config"]
            c = ha_ConfigParser(
                converters={"list": lambda x: [i.strip() for i in x.split(",")]},
                ha_args=settings,
            )
            c.read(configfile, encoding="utf-8")
            c.configfile = configfile
            logging.info(
                "Using config file '{0}' from the 'config' key of YAML file {1}".format(
                    configfile, args.settings
                )
            )
        except Exception as e:
            logging.error(
                f"Error parsing config.ini '{configfile}'. No valid configuration file. {e}."
            )
            os.sys.exit(1)
    else:
        try:
            c = ha_ConfigParser(ha_args=settings)
            c.configfile = None
        except Exception as e:
            logging.error("Config parser problem '{0}'".format(e))
            os.sys.exit(1)
    return c


def get_config_from_files(args):
    c = None
    if args.debug:
        ha_args["debug"] = args.debug
    if args.interval:
        ha_args["interval"] = args.interval
    if args.data_config:
        ha_args["data_config"] = args.data_config
    if args.persistant_cache_file:
        ha_args["persistant_cache_file"] = args.persistant_cache_file
    if os.path.isfile(args.settings):
        if os.path.isfile(args.config):
            logging.warning(
                "Multiple config files found at '{0}' or '{1}', "
                "using '{0}', ignoring config from command line option '{1}'.'".format(
                    args.settings, args.config
                )
            )

        settings = get_yaml_settings(args)
        # commandline override
        settings.update(ha_args)
        c = setup_config_parser(args, settings)
    if os.path.isfile(args.config) and not os.path.isfile(args.settings):
        ha_args["config"] = args.config
        c = ha_ConfigParser(
            converters={"list": lambda x: [i.strip() for i in x.split(",")]},
            ha_args=ha_args,
        )
        c.read([args.config], encoding="utf-8")
        c.configfile = args.config
    if not c:
        logging.error("No valid configuration found. Exiting!")
        os.sys.exit(1)
    return c


if __name__ == "__main__":
    stopflag = False
    home = os.path.expanduser("~")
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--settings",
        default=os.path.join(home, ".omnik/config.yaml"),
        help="Path to .yaml configuration file",
        metavar="FILE",
    )
    parser.add_argument(
        "--section",
        default=None,
        help="Section to .yaml configuration file to use. Defaults to the first section found.",
    )
    parser.add_argument(
        "--config",
        default=os.path.join(home, ".omnik/config.ini"),
        help="Path to configuration file (ini) (DECREPATED!)",
        metavar="FILE",
    )
    parser.add_argument(
        "--data_config",
        help="Path to data_fields.json configuration file",
        metavar="FILE",
    )
    parser.add_argument(
        "--persistant_cache_file",
        help="Path to writable cache json file to store last power en total energy",
        metavar="FILE",
    )
    parser.add_argument("--interval", type=int, help="Execute every n seconds")

    parser.add_argument("-d", "--debug", action="store_true", help="Debug mode")

    args = parser.parse_args()

    if not os.path.isfile(args.settings) and not os.path.isfile(args.config):
        logging.critical(
            "Unable to find config at '{0}' or {1}".format(args.settings, args.config)
        )
        parser.print_help()
        os.sys.exit(1)
    elif os.path.isfile(args.config):
        logging.warning(
            "The use of a classig config.ini is decrepated! "
            "Use the --settings option. See documentation."
        )

    main(get_config_from_files(args), hass_api=None)
