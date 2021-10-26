import pytz
import json
import time
import ssl

from omnik.ha_logger import hybridlogger

import paho.mqtt.client as mqttclient
import uuid

from omnik.plugin_output import Plugin
import threading

MEASUREMENT_CLASSES = [
    "power",
    "current",
    "temperature",
    "voltage",
    "frequency",
    "flow",
]
MEASUREMENT_TOTAL_INCREASING_CLASSES = ["energy", "gas", "operation_time", "count"]
STATE_CLASS_MEASUREMENT = "measurement"
STATE_CLASS_TOTAL_INCREASING = "total_increasing"


class mqtt(Plugin):
    def __init__(self):
        super().__init__()
        self.name = "mqtt"
        self.description = "Write output to internal mqtt facility of Home Assistant"
        tz = self.config.get("default", "timezone", fallback="Europe/Amsterdam")
        self.timezone = pytz.timezone(tz)

        self.mqtt_client_name = (
            self.config.get(
                "output.mqtt", "client_name_prefix", fallback="ha-mqtt-omniklogger"
            )
            + "_"
            + uuid.uuid4().hex
        )
        self.mqtt_host = self.config.get("output.mqtt", "host", fallback="localhost")
        self.mqtt_port = int(self.config.get("output.mqtt", "port", fallback="1833"))

        self.tls = self.config.getboolean("output.mqtt", "tls", fallback=False)
        self.ca_certs = self.config.get("output.mqtt", "ca_certs", fallback=None)
        self.client_cert = self.config.get("output.mqtt", "client_cert", fallback=None)
        self.client_key = self.config.get("output.mqtt", "client_key", fallback=None)

        self.mqtt_retain = self.config.getboolean(
            "output.mqtt", "retain", fallback=False
        )
        self.mqtt_config_published = {}
        if not self.config.has_option(
            "output.mqtt", "username"
        ) or not self.config.has_option("output.mqtt", "password"):
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                "Please specify MQTT username and password in the configuration",
            )
            self.mqtt_username = None
            self.mqtt_password = None
        else:
            self.mqtt_username = self.config.get("output.mqtt", "username")
            self.mqtt_password = self.config.get("output.mqtt", "password")

        # mqtt setup
        self.mqtt_client = mqttclient.Client(self.mqtt_client_name)
        self.mqtt_client.on_connect = self._mqtt_on_connect  # bind call back function
        self.mqtt_client.on_disconnect = (
            self._mqtt_on_disconnect
        )  # bind call back function
        self.mqtt_client.logger = self.logger
        self.mqtt_client.hass_api = self.hass_api
        # self.mqtt_client.on_message=mqtt_on_message (not used)
        self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
        # TLS support
        if self.tls:
            self.mqtt_client.tls_set(
                ca_certs=self.ca_certs or None,
                certfile=self.client_cert or None,
                keyfile=self.client_key or None,
            )
        if self.config.has_option("output.mqtt", "discovery_prefix"):
            self.discovery_prefix = self.config.get("output.mqtt", "discovery_prefix")
        else:
            self.discovery_prefix = "homeassistant"
        # Init topics dict
        self.topics = {}
        # Init config dict
        self.config_pl = {}
        # Make instance to run exclusively
        self.access = threading.Condition(threading.Lock())
        self._connected = self.mqtt_connect()

    def mqtt_connect(self) -> bool:
        try:
            # connect
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port)
            # start processing messages
            self.mqtt_client.loop_start()
            return True
        except OSError as ex:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                f"Unable to connect to MQTT server, is your configuration correct? MQTT was not initialized correctly. Error: {ex}",
            )
            return False

    def _init_config(self, msg):
        # Check if init is needed
        asset_classes = set()
        for field in msg:
            if field in self.config.data_field_config:
                asset_class = self.config.data_field_config[field]["asset"]
                if asset_class not in asset_classes:
                    asset_classes.add(asset_class)

        # Init from using mqtt field config (loaded from json)
        # self.config.data_field_config
        # field: name, dev_cla, ic, unit, measurement, filter, asset

        # Assemble topics
        self.topics[msg["plant_id"]] = self._topics(msg, asset_classes)

        # Assemble config
        self.config_pl[msg["plant_id"]] = self._config_payload(
            msg, self.topics[msg["plant_id"]], asset_classes
        )

        # Flag init as done
        # self.mqtt_field_name_override_init[msg['plant_id']] = True
        return asset_classes

    def _mqtt_on_connect(self, client, userdata, flags, rc=0, properties=None):
        if rc == 0:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO", "MQTT connected")
            # subscribe listening (not used)

    def _mqtt_on_disconnect(self, client, userdata, flags, rc=0):
        if rc == 0:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO", "MQTT disconnected")

    def _topics(self, msg, asset_classes):
        # Init from using mqtt field config (loaded from json)
        # self.config.data_field_config
        # field: name, dev_cla, ic, unit, filter
        topic_suffix = f"_{msg['plant_id']}" if not msg["plant_id"] == "0" else ""
        topics = {}
        for asset_class in asset_classes:
            device_name = self.config.attributes["devicename"][
                self.config.attributes["device_identifier"][asset_class]
            ]
            topics[asset_class] = {}
            topics[asset_class][
                "main"
            ] = f"{self.discovery_prefix}/sensor/{device_name}{topic_suffix}"
            topics[asset_class][
                "state"
            ] = f"{topics[asset_class]['main']}/{asset_class}_state"
            topics[asset_class]["attr"] = f"{topics[asset_class]['main']}/attr"
            topics[asset_class]["config"] = {}
            for field in self.config.data_field_config:
                if field in msg:
                    topics[asset_class]["config"][
                        field
                    ] = f"{topics[asset_class]['main']}/{field}/config"
        return topics

    def _device_payload(self, msg, asset_classes):
        device_pl = {}
        for asset_class in asset_classes:
            device_pl[asset_class] = {}
            # Set device_name
            device_name = self.config.attributes["devicename"][
                self.config.attributes["device_identifier"][asset_class]
            ]
            # Determine appendixes
            name_appendix = ""
            identifier = self.config.attributes["identifier"][asset_class]
            if identifier in msg and self.config.getboolean(
                "output.mqtt", "append_plant_id", False
            ):
                name_appendix = f" {msg[identifier]}"
            id_prefix = ""
            if identifier in msg:
                id_prefix = f"{msg[identifier]}_"
            # Device payload
            device_pl[asset_class] = {
                "identifiers": [
                    f"{id_prefix}{self.config.attributes['device_identifier'][asset_class]}"
                ],
                "name": f"{device_name}{name_appendix}",
                "mdl": self.config.attributes["model"][asset_class],
                "mf": self.config.attributes["mf"][asset_class],
            }
        return device_pl

    def _config_payload(self, msg, topics, asset_classes):
        # Get device payload
        device_pl = self._device_payload(msg, asset_classes)

        # Fill config_pl dict
        # Init from using mqtt field config (loaded from json)
        # self.config.data_field_config
        config_pl = {}

        # Generate MQTT config topics
        for field in self.config.data_field_config:
            # Only generate config for available data
            if field not in msg:
                # skip publishing non exitent values
                continue
            asset_class = self.config.data_field_config[field]["asset"]
            if not asset_class:
                # skip publication
                continue
            # field: name, dev_cla, ic, unit, measurent, filter, asset
            if self.config.has_option("output.mqtt", f"{field}_name"):
                fieldname = self.config.get("output.mqtt", f"{field}_name")
            else:
                fieldname = self.config.data_field_config[field]["name"]
            identifier = self.config.attributes["identifier"][asset_class]
            config_pl[field] = {
                "~": f"{topics[asset_class]['main']}",
                "uniq_id": f"{msg[identifier]}_{field}",
                "name": f"{fieldname}",
                "stat_t": f"~/{asset_class}_state",
                "json_attr_t": "~/attr",
                "val_tpl": f"{{{{(value_json.{field}{self.config.data_field_config[field]['filter']})}}}}",
                "dev": device_pl[asset_class],
            }

            # Set device and state class if configured
            if self.config.data_field_config[field]["dev_cla"]:
                config_pl[field]["dev_cla"] = self.config.data_field_config[field][
                    "dev_cla"
                ]
            if (
                self.config.data_field_config[field]["dev_cla"]
                in MEASUREMENT_TOTAL_INCREASING_CLASSES
            ):
                state_class = STATE_CLASS_TOTAL_INCREASING
            elif self.config.data_field_config[field]["dev_cla"] in MEASUREMENT_CLASSES:
                state_class = STATE_CLASS_MEASUREMENT
            else:
                state_class = None

            # set the state class for measurements
            if state_class:
                config_pl[field]["stat_cla"] = state_class
            # Set icon if configured
            if self.config.data_field_config[field]["ic"]:
                config_pl[field][
                    "ic"
                ] = f"mdi:{self.config.data_field_config[field]['ic']}"
            # Set unit of measurement if configured
            if self.config.data_field_config[field]["unit"]:
                config_pl[field]["unit_of_meas"] = self.config.data_field_config[field][
                    "unit"
                ]

        return config_pl

    def _value_payload(self, msg):
        value_pl = {}
        # Generate MQTT config topics
        for field in self.config.data_field_config:
            # field: name, dev_cla, ic, unit, filter
            # Only generate payload for available data
            asset_class = self.config.data_field_config[field]["asset"]
            if not asset_class:
                # skip publication
                continue
            if asset_class not in value_pl:
                value_pl[asset_class] = {}
            if field in msg:
                value_pl[asset_class][field] = self.jsonval(msg[field])

        return value_pl

    def _attribute_payload(self, msg, asset_classes):
        attr_pl = {}
        for asset_class in asset_classes:
            apl = self._attribute_payload_asset_class(msg, asset_class)
            if apl:
                attr_pl[asset_class] = apl
        return attr_pl

    def _attribute_payload_asset_class(self, msg, asset_class):
        attr_pl_class = {}
        for attr in self.config.attributes["asset"][asset_class]:
            attr_pl = self._encode_attribute(msg, attr)
            if attr_pl:
                attr_pl_class[attr] = self._encode_attribute(msg, attr)
        return attr_pl_class

    def _encode_attribute(self, msg, attr):
        if attr not in msg:
            return None
        if attr in self.config.data_field_config:
            return (
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(msg[attr]))
                if self.config.data_field_config[attr]["dev_cla"] == "timestamp"
                else self.jsonval(msg[attr])
            )
        else:
            return self.jsonval(msg[attr])

    def _publish_config(self, msg):
        new_asset_classes = set()
        if msg["plant_id"] not in self.mqtt_config_published:
            # init mqtt_config_published flag cache
            self.mqtt_config_published[msg["plant_id"]] = set()

        for entity in self.config_pl[msg["plant_id"]]:
            asset_class = self.config.data_field_config[entity]["asset"]
            if (
                asset_class in self.mqtt_config_published[msg["plant_id"]]
                and self.mqtt_retain
            ):
                continue
            else:
                self._publish_config_entity(
                    self.topics[msg["plant_id"]][asset_class],
                    self.config_pl[msg["plant_id"]],
                    entity,
                )
                new_asset_classes.add(asset_class)
        for item in new_asset_classes:
            self.mqtt_config_published[msg["plant_id"]].add(item)

    def _publish_config_entity(self, topics, config_pl, entity):
        try:
            # publish config
            # asset_class = self.config.data_field_config[entity]['asset']
            if self.mqtt_client.publish(
                topics["config"][entity],
                json.dumps(config_pl[entity]),
                retain=self.mqtt_retain,
            ):
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "DEBUG",
                    f"Publishing config {json.dumps(config_pl[entity])} "
                    f"to {topics['config'][entity]} successful.",
                )
            else:
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "WARNING",
                    f"Publishing config {json.dumps(config_pl[entity])} "
                    f"to {topics['config'][entity]} failed!",
                )
        except Exception as e:
            hybridlogger.ha_log(
                self.logger,
                self.hass_api,
                "ERROR",
                f"Unhandled error publishing config for entity {entity}: {e}",
            )

    def _publish_attributes(self, msg, asset_classes):

        attr_pl = self._attribute_payload(msg, asset_classes)
        for asset_class in asset_classes:
            try:
                # publish attributes
                if self.mqtt_client.publish(
                    self.topics[msg["plant_id"]][asset_class]["attr"],
                    json.dumps(attr_pl[asset_class]),
                    retain=self.mqtt_retain,
                ):
                    hybridlogger.ha_log(
                        self.logger,
                        self.hass_api,
                        "DEBUG",
                        f"Publishing attributes {json.dumps(attr_pl[asset_class])} to "
                        f"{self.topics[msg['plant_id']][asset_class]['attr']} successful.",
                    )
                else:
                    hybridlogger.ha_log(
                        self.logger,
                        self.hass_api,
                        "WARNING",
                        f"Publishing attributes {json.dumps(attr_pl[asset_class])} to "
                        f"{self.topics[msg['plant_id']][asset_class]['attr']} failed!",
                    )
            except Exception as e:
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "ERROR",
                    f"Unhandled error publishing attributes: {e}",
                )

    def _publish_state(self, topics, value_pl, asset_classes):
        for asset_class in asset_classes:
            try:
                # publish state
                if self.mqtt_client.publish(
                    topics[asset_class]["state"],
                    json.dumps(value_pl[asset_class]),
                    retain=self.mqtt_retain,
                ):
                    hybridlogger.ha_log(
                        self.logger,
                        self.hass_api,
                        "DEBUG",
                        f"Publishing state {json.dumps(value_pl[asset_class])} to "
                        f"{topics[asset_class]['state']} successful.",
                    )
                else:
                    hybridlogger.ha_log(
                        self.logger,
                        self.hass_api,
                        "WARNING",
                        f"Publishing state {json.dumps(value_pl[asset_class])} to "
                        f"{topics[asset_class]['state']} failed!",
                    )
            except Exception as e:
                hybridlogger.ha_log(
                    self.logger,
                    self.hass_api,
                    "ERROR",
                    f"Unhandled error publishing states: {e}",
                )

    def process(self, **args):
        """
        Send data to over mqtt (compliant with Home Assistant MQTT discovery standard
        See: https://www.home-assistant.io/docs/mqtt/discovery/)
        """

        # Check if we have a valid loop
        if not self._connected:
            self._connected = self.mqtt_connect()
            if not self._connected:
                return

        self.access.acquire()

        # Get argument
        msg = args["msg"]

        # Assemble config
        asset_classes = self._init_config(msg)

        # Publish config
        self._publish_config(msg)

        # publish attributes
        self._publish_attributes(msg, asset_classes)

        # publish state
        value_pl = self._value_payload(msg)
        self._publish_state(self.topics[msg["plant_id"]], value_pl, asset_classes)

        self.access.release()
