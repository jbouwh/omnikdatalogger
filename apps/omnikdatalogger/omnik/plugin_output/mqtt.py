import json
import time
from omnik.ha_logger import hybridlogger

import paho.mqtt.client as mqttclient
import uuid

from omnik.plugin_output import Plugin


class mqtt(Plugin):

    def __init__(self):
        super().__init__()
        self.name = 'mqtt'
        self.description = 'Write output to internal mqtt facility of Home Assistant'
        # tz = self.config.get('default', 'timezone',
        #                      fallback='Europe/Amsterdam')
        # self.timezone = pytz.timezone(tz)

        self.mqtt_client_name = self.config.get('output.mqtt', 'client_name_prefix',
                                                fallback='ha-mqtt-omniklogger') + "_" + uuid.uuid4().hex
        self.mqtt_host = self.config.get('output.mqtt', 'host', fallback='localhost')
        self.mqtt_port = int(self.config.get('output.mqtt', 'port', fallback='1833'))
        self.mqtt_retain = self.config.getboolean('output.mqtt', 'retain', fallback=False)
        self.mqtt_config_published = {}
        if not self.config.has_option('output.mqtt', 'username') or not self.config.has_option('output.mqtt', 'password'):
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",
                                "Please specify MQTT username and password in the configuration")
        else:
            self.mqtt_username = self.config.get('output.mqtt', 'username')
            self.mqtt_password = self.config.get('output.mqtt', 'password')

        # mqtt setup
        self.mqtt_client = mqttclient.Client(self.mqtt_client_name)
        self.mqtt_client.on_connect = self._mqtt_on_connect  # bind call back function
        self.mqtt_client.on_disconnect = self._mqtt_on_disconnect  # bind call back function
        self.mqtt_client.logger = self.logger
        self.mqtt_client.hass_api = self.hass_api
        # self.mqtt_client.on_message=mqtt_on_message (not used)
        self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
        self.mqtt_client.connect(self.mqtt_host, self.mqtt_port)
        # start processing messages
        self.mqtt_client.loop_start()
        if self.config.has_option('output.mqtt', 'discovery_prefix'):
            self.discovery_prefix = self.config.get('output.mqtt', 'discovery_prefix')
        else:
            self.discovery_prefix = "homeassistant"
        # The mqtt name of the inverter device
        # use the configured device name or the device name from the omnik portal
        if self.config.has_option('output.mqtt', 'device_name'):
            self.device_name = self.config.get('output.mqtt', 'device_name')
        else:
            self.device_name = None
        # self.config.mqtt_fields['<field_name>']['name'] can have an override
        self.mqtt_field_name_override_init = {}
        # Init topics dict
        self.topics = {}
        # Init config dict
        self.config_pl = {}

    def _init_config(self, msg):
        # Check if init is needed
        if msg['plant_id'] in self.mqtt_field_name_override_init:
            return
        # Init from using mqtt field config (loaded from json)
        # self.config.data_field_config
        # field: name, dev_cla, ic, unit, filter

        # Assemble topics
        self.topics[msg['plant_id']] = self._topics(msg)

        # Assemble config
        self.config_pl[msg['plant_id']] = self._config_payload(msg, self.topics[msg['plant_id']])

        # Flag init as done
        self.mqtt_field_name_override_init[msg['plant_id']] = True

    def _mqtt_on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO", "MQTT connected")
            # subscribe listening (not used)

    def _mqtt_on_disconnect(self, client, userdata, flags, rc):
        if rc == 0:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO", "MQTT disconnected")

    def _topics(self, msg):
        # Init from using mqtt field config (loaded from json)
        # self.config.data_field_config
        # field: name, dev_cla, ic, unit, filter

        topics = {}
        topics['main'] = f"{self.discovery_prefix}/sensor/{self.device_name}_{msg['plant_id']}"
        topics['state'] = f"{topics['main']}/state"
        topics['attr'] = f"{topics['main']}/attr"
        topics['config'] = {}
        for field in self.config.data_field_config:
            if field in msg:
                topics['config'][field] = f"{topics['main']}/{field}/config"
        return topics

    def _device_payload(self, msg):
        # Determine model
        model = "Omnik data logger"

        # Set device_name
        if self.device_name:
            device_name = self.device_name
        else:
            device_name = msg['name']

        # Determine plant appendix
        plant_appendix = ""
        if self.config.getboolean('output.mqtt', 'append_plant_id', False):
            plant_appendix = f" [{msg['plant_id']}]"

        # Device payload
        device_pl = {
            "identifiers": [f"omnik_{msg['plant_id']}"],
            "name": f"{device_name}{plant_appendix}",
            "mdl": model,
            "mf": 'Omnik'
            }
        return device_pl

    def _config_payload(self, msg, topics):
        # Get device payload
        device_pl = self._device_payload(msg)

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
            # field: name, dev_cla, ic, unit, filter
            if self.config.has_option('output.mqtt', f'{field}_name'):
                fieldname = self.config.get('output.mqtt', f'{field}_name')
            else:
                fieldname = self.config.data_field_config[field]['name']
            config_pl[field] = {
                "~": f"{topics['main']}",
                "uniq_id": f"{msg['plant_id']}_{field}",
                "name": f"{fieldname}",
                "stat_t": "~/state",
                "json_attr_t": "~/attr",
                "val_tpl": f"{{{{(value_json.{field}{self.config.data_field_config[field]['filter']})}}}}",
                "dev": device_pl
                }
            # Set device class if configured
            if self.config.data_field_config[field]['dev_cla']:
                config_pl[field]['dev_cla'] = self.config.data_field_config[field]['dev_cla']
            # Set icon if configured
            if self.config.data_field_config[field]['ic']:
                config_pl[field]['ic'] = f"mdi:{self.config.data_field_config[field]['ic']}"
            # Set unit of measurement if configured
            if self.config.data_field_config[field]['unit']:
                config_pl[field]['unit_of_meas'] = self.config.data_field_config[field]['unit']

        return config_pl

    def _value_payload(self, msg):
        value_pl = {}
        # Generate MQTT config topics
        for field in self.config.data_field_config:
            # field: name, dev_cla, ic, unit, filter
            # Only generate payload for available data
            if field in msg:
                value_pl[field] = msg[field]

        return value_pl

    def _attribute_payload(self, msg):
        attr_pl = {
            "inverter": msg['inverter'],
            "plant_id": int(msg['plant_id']),
            "last_update": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg['last_update']))
            }
        return attr_pl

    def _publish_config(self, msg):
        if self.mqtt_retain and msg['plant_id'] in self.mqtt_config_published:
            # Do not republish config if retain flag is used
            return
        for entity in self.config_pl[msg['plant_id']]:
            self._publish_config_entity(self.topics[msg['plant_id']], self.config_pl[msg['plant_id']], entity)
        # Flag config as published
        self.mqtt_config_published[msg['plant_id']] = True

    def _publish_config_entity(self, topics, config_pl, entity):
        try:
            # publish config
            if self.mqtt_client.publish(topics['config'][entity], json.dumps(config_pl[entity]), retain=self.mqtt_retain):
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Publishing config {json.dumps(config_pl[entity])} "
                                    f"to {topics['config'][entity]} successful.")
            else:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",
                                    f"Publishing config {json.dumps(config_pl[entity])} "
                                    f"to {topics['config'][entity]} failed!")
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",
                                f"Unhandled error publishing config for entity {entity}: {e}")

    def _publish_attributes(self, topics, attr_pl):
        try:
            # publish attributes
            if self.mqtt_client.publish(topics['attr'], json.dumps(attr_pl), retain=self.mqtt_retain):
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Publishing attributes {json.dumps(attr_pl)} to "
                                    f"{topics['attr']} successful.")
            else:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",
                                    f"Publishing attributes {json.dumps(attr_pl)} to "
                                    f"{topics['attr']} failed!")
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", f"Unhandled error publishing attributes: {e}")

    def _publish_state(self, topics, value_pl):
        try:
            # publish state
            if self.mqtt_client.publish(topics['state'], json.dumps(value_pl), retain=self.mqtt_retain):
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Publishing state {json.dumps(value_pl)} to "
                                    f"{topics['state']} successful.")
            else:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",
                                    f"Publishing state {json.dumps(value_pl)} to "
                                    f"{topics['state']} failed!")
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", f"Unhandled error publishing states: {e}")

    def process(self, **args):
        """
        Send data to over mqtt (compliant with Home Assistant MQTT discovery standard
        See: https://www.home-assistant.io/docs/mqtt/discovery/)
        """
        # Get argument
        msg = args['msg']

        # Set report time in local timezone
        msg['reporttime'] = time.localtime(msg['last_update'])

        # Assemble config
        self._init_config(msg)

        # Publish config
        self._publish_config(msg)

        # publish attributes
        attr_pl = self._attribute_payload(msg)
        self._publish_attributes(self.topics[msg['plant_id']], attr_pl)

        # publish state
        value_pl = self._value_payload(msg)
        self._publish_state(self.topics[msg['plant_id']], value_pl)
