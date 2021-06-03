import requests
from omnik.ha_logger import hybridlogger

from omnik.plugin_output import Plugin
import threading


class influxdb(Plugin):
    def __init__(self):
        super().__init__()
        self.name = "influxdb"
        self.description = "Write output to InfluxDB"
        self.host = self.config.get("output.influxdb", "host", fallback="localhost")
        self.port = self.config.get("output.influxdb", "port", fallback="8086")
        self.database = self.config.get(
            "output.influxdb", "database", fallback="omnikdatalogger"
        )

        self.headers = {"Content-type": "application/x-www-form-urlencoded"}
        # Add JWT authentication token
        if self.config.has_option("output.influxdb", "jwt_token"):
            self.auth = None
            self.headers[
                "Authorization"
            ] = f"Bearer {self.config.get('output.influxdb', 'jwt_token')}"
        elif self.config.has_option(
            "output.influxdb", "username"
        ) and self.config.has_option("output.influxdb", "password"):
            self.auth = requests.auth.HTTPBasicAuth(
                self.config.get("output.influxdb", "username"),
                self.config.get("output.influxdb", "password"),
            )
        else:
            self.auth = None
        self.timestamp_field = {}
        for field in self.config.data_field_config:
            if not self.config.data_field_config[field]["dev_cla"] == "timestamp":
                continue
            self.timestamp_field[self.config.data_field_config[field]["asset"]] = field
        self.access = threading.Condition(threading.Lock())

    def _get_temperature(self, values):
        if self.config.getboolean("output.influxdb", "use_temperature", fallback=False):
            weather = self.get_weather()
            values["temperature"] = str(weather["main"]["temp"])
            values["timestamp_ow"] = weather["main"]["dt"]

    def _get_attributes(self, values, asset_class):
        attributes = {}
        for att in self.config.attributes["asset"][asset_class]:
            if att in self.config.data_field_config:
                if self.config.data_field_config[att]["dev_cla"] == "timestamp":
                    continue
            attributes[att] = values[att]
        return attributes.copy()

    def _get_tags(self, field, attributes, asset_class):
        tags = attributes.copy()
        tags["asset"] = asset_class
        tags["entity"] = field
        tags["name"] = str(self.config.data_field_config[field]["name"]).replace(
            " ", "\\ "
        )
        if self.config.data_field_config[field]["dev_cla"]:
            tags["dev_cla"] = self.config.data_field_config[field]["dev_cla"]
        if self.config.data_field_config[field]["unit"]:
            tags["unit"] = str(self.config.data_field_config[field]["unit"]).replace(
                " ", "\\ "
            )
        tags.update(self.config.data_field_config[field]["tags"])
        return tags.copy()

    def _format_output(self, field, values):
        if field not in self.config.data_field_config:
            return ""
        if not self.config.data_field_config[field]["measurement"]:
            # no measurement, exclude
            return ""

        if self.config.data_field_config[field]["dev_cla"] == "timestamp":
            # skip the epoch fields
            return ""

        asset_class = self.config.data_field_config[field]["asset"]
        attributes = self._get_attributes(values, asset_class)
        nanoepoch = int(values[self.timestamp_field[asset_class]] * 1000000000)

        if field in values and self.config.data_field_config:
            # Get tags
            tags = self._get_tags(field, attributes, asset_class)
            # format output data using the InfluxDB line protocol
            # https://v2.docs.influxdata.com/v2.0/write-data/#line-protocol
            return (
                f'{self.config.data_field_config[field]["measurement"]},'
                f'{",".join("{}={}".format(key, value) for key, value in tags.items())} '
                f"value={values[field]} {nanoepoch}\n"
            )
        else:
            return ""

    def process(self, **args):
        # Send data to influxdb
        try:
            self.access.acquire()
            msg = args["msg"]
            hybridlogger.ha_log(
                self.logger, self.hass_api, "DEBUG", f"Logging data to InfluxDB: {msg}"
            )
            values = msg.copy()
            # self._get_temperature(values)

            # Build structure
            encoded = ""
            for field in values:
                encoded += self._format_output(field, values)

            # Influx has no tables! Use measurement prefix
            # encoded = f'inverter,plant=p1 {",".join("{}={}".format(key, value)
            # for key, value in values.items())} {nanoepoch}'

            # curl -i -XPOST 'http://localhost:8086/write?db=mydb' --data-binary
            # 'cpu_load_short,host=server01,region=us-west value=0.64 1434055562000000000'
            url = f"http://{self.host}:{self.port}/write?db={self.database}"

            r = requests.post(url, data=encoded, headers=self.headers, auth=self.auth)

            r.raise_for_status()
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "DEBUG",
                f"Submit to Influxdb {url} successful.",
            )
        except requests.exceptions.HTTPError as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                f"Got error from influxdb: {e.args} (ignoring: if this happens a lot ... fix it)",
            )
        except Exception as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                f"Got unknown submitting to influxdb: {e.args} (ignoring: if this happens a lot ... fix it)",
            )
        finally:
            self.access.release()
