from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError
import requests
from omnik.ha_logger import hybridlogger

from omnik.plugin_output import Plugin
import threading


class influxdb(Plugin):
    def __init__(self):
        super().__init__()
        self.auth = None
        self.client = None
        self.name = "influxdb"
        self.description = "Write output to InfluxDB"
        # common settings
        self.host = self.config.get("output.influxdb", "host", fallback="localhost")
        self.port = self.config.get("output.influxdb", "port", fallback="8086")
        self.ssl = self.config.getboolean("output.influxdb", "ssl", fallback=False)
        self.verify_ssl = self.config.getboolean(
            "output.influxdb", "verify_ssl", fallback=True
        )
        self.ssl_ca_cert = self.config.get("output.influxdb", "ssl_ca_cert")
        self.path = self.config.get("output.influxdb", "path")

        # Influx version 1 settings
        self.database = self.config.get(
            "output.influxdb", "database", fallback="omnikdatalogger"
        )

        self.headers = {"Content-type": "application/x-www-form-urlencoded"}
        # Add JWT authentication token
        if self.config.has_option("output.influxdb", "jwt_token"):
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
        # Influx vs 2 settings
        self.org = self.config.get("output.influxdb", "org")
        self.bucket = self.config.get("output.influxdb", "bucket")
        self.token = self.config.get("output.influxdb", "token")
        self.auth_v2 = False
        if self.org and self.bucket and self.token:
            self.auth_v2 = True
            # Log warning if that v1 auth will be ignored
            if self.auth:
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "WARNING",
                    "Ignoring InfluxDB v1 settings database, username, password and jwt_token",
                )
            protocol = "https" if self.ssl else "http"
            path = f"/{self.path}" if self.path else ""
            url = f"{protocol}://{self.host}:{self.port}{path}"
            self.client = InfluxDBClient(
                url=url,
                token=self.token,
                org=self.org,
                verify_ssl=self.verify_ssl,
                ssl_ca_cert=self.ssl_ca_cert,
            )
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                "InfluxDB v2 client initialized",
            )
        else:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "INFO",
                "InfluxDB v1 client initialized",
            )
            if not self.auth:
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "WARNING",
                    "Authentication was set or incomplete!",
                )

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
        nanoepoch = int(
            values[self.timestamp_field.get(asset_class) or "last_update"] * 1000000000
        )

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
            # Log output fields
            self.log_available_fields(msg)

            values = msg.copy()

            # Build structure
            encoded = ""
            for field in values:
                encoded += self._format_output(field, values)

            # Influx has no tables! Use measurement prefix
            # encoded = f'inverter,plant=p1 {",".join("{}={}".format(key, value)
            # for key, value in values.items())} {nanoepoch}'

            # (v1) curl -i -XPOST 'http://localhost:8086/write?db=mydb' --data-binary
            # 'cpu_load_short,host=server01,region=us-west value=0.64 1434055562000000000'
            if self.auth_v2 and self.client:
                with self.client.write_api(write_options=SYNCHRONOUS) as _client:
                    _client.write(bucket=self.bucket, record=encoded)
            else:
                url = f"{'https' if self.ssl else 'http'}://{self.host}:{self.port}/write?db={self.database}"

                r = requests.post(
                    url,
                    data=encoded,
                    headers=self.headers,
                    auth=self.auth,
                    verify=self.verify_ssl,
                )

                r.raise_for_status()

        except InfluxDBError as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                f"Got error from influxdb2: {e.args} (ignoring: if this happens a lot ... fix it)",
            )

        except requests.exceptions.ConnectionError as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                f"Got error from influxdb: {e.args} (ignoring: if this happens a lot ... fix it)",
            )

        except requests.exceptions.RequestException as err:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "WARNING",
                f"Unhandled RequestException error: {err}",
            )

        finally:
            self.access.release()
