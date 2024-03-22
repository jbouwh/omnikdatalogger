import csv
import threading
from time import strftime, localtime
from os import path
import time
from omnik.ha_logger import hybridlogger

from omnik.plugin_output import Plugin

DEFAULT_FIELDS = [
    "date",
    "time",
    "current_power",
    "today_energy",
    "total_energy",
]


def _ensure_headers(csvfile, fields, separator, no_headers):
    """Open the file and make sure the correct headers are present."""
    headers = None
    if path.isfile(csvfile):
        # Check existing file
        with open(csvfile, "r", newline="\n") as file_object:
            reader = csv.reader(file_object, delimiter=separator)
            for row in reader:
                headers = row
                break

        # If no headers are used, we cannot check them, but we check the number fields, return None if there is no count match
        if no_headers:
            return fields.copy() if len(headers or []) == len(fields) else None
        # return existing headers or None if an existing file does not comply the field and seperator settings
        if headers:
            return headers if len(fields) == len(set(fields) & set(headers)) else None
    # Create a file with headers

    with open(csvfile, "w", newline="\n") as file_object:
        headers = fields.copy()
        if not no_headers:
            writer = csv.writer(file_object, delimiter=separator)
            writer.writerow(headers)

    return headers


class csvoutput(Plugin):
    def __init__(self):
        super().__init__()
        self.name = "csvoutput"
        self.description = "Write output to a text file"
        # Enable support for aggregates and detail output
        self.process_aggregates = True
        self.process_output = True
        # Make instance to run exclusively
        self.access = threading.Condition(threading.Lock())
        hybridlogger.ha_log(
            self.logger,
            self.hass_api,
            "INFO",
            "CSV output plugin enabled.",
        )

    def _get_temperature(self, msg, config_section):
        """Get the temperature from the open weater API"""
        if self.config.getboolean(config_section, "use_temperature", fallback=False):
            weather = self.get_weather()
            msg["temperature"] = weather["main"]["temp"]

    def process(self, **args):
        """
        Send data to csv
        """
        # Assign output file and fields to log
        msg = args["msg"]
        # Do not log cached data
        if msg.get("cached"):
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "DEBUG",
                "Ignoring previously cached data for CSV output.",
            )
            return
        config_section = (
            f'plant.{msg.get("plant_id")}' if msg.get("plant_id") else "output.csv"
        )
        csvfile = self.config.get(config_section, "csvfile", fallback=None)
        separator = self.config.get(config_section, "separator", fallback=";")
        fields = self.config.getlist(config_section, "fields", fallback=DEFAULT_FIELDS)
        no_headers = self.config.getboolean(
            config_section, "no_headers", fallback=False
        )
        if fields and fields[0] and csvfile:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "DEBUG",
                f"CSV output: {fields}. Config key '{config_section}'.",
            )
        else:
            if not csvfile:
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "DEBUG",
                    f"Skipping CSV logging, no output file defined. Config key '{config_section}'",
                )
            else:
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "WARNING",
                    f"No output fields configured! CSV monitoring disabled. Config key '{config_section}'",
                )
            return
        try:
            self.access.acquire()
            # Ensure headers
            headers = _ensure_headers(csvfile, fields, separator, no_headers)
            if not headers:
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "ERROR",
                    "Skipping CSV logging, file exists with invalid header structure or unequal field count.",
                )
            else:
                # Append the log
                with open(csvfile, "a") as file_object:
                    reporttime = localtime(msg.get("last_update", time.time()))
                    self._get_temperature(msg, config_section)
                    msg.update(
                        {
                            "date": strftime("%Y-%m-%d", reporttime),
                            "time": strftime("%H:%M:%S", reporttime),
                        }
                    )
                    # Log output fields
                    self.log_available_fields(msg)
                    # write field to csv file
                    fields = list()
                    for field in headers:
                        fields.append(msg.get(field))
                    writer = csv.writer(file_object, delimiter=separator)
                    writer.writerow(fields)

        except OSError as os_err:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                f"File exception error for '{csvfile}': {os_err.args}",
            )
        finally:
            self.access.release()
