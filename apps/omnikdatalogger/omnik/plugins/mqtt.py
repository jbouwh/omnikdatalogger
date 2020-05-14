import json
from datetime import datetime
import pytz
from ha_logger import hybridlogger

import paho.mqtt.client as mqttclient
import uuid


from omnik.plugins import Plugin


class mqtt(Plugin):

    def __init__(self):
        super().__init__()
        self.name = 'mqtt'
        self.description = 'Write output to internal mqtt facility of Home Assistant'
        tz = self.config.get('default', 'timezone',
                             fallback='Europe/Amsterdam')
        self.timezone = pytz.timezone(tz)

        self.mqtt_client_name = self.config.get('mqtt', 'client_name_prefix',
                                                fallback='ha-mqtt-omniklogger') + "_" + uuid.uuid4().hex
        self.mqtt_host = self.config.get('mqtt', 'host', fallback='localhost')
        self.mqtt_port = int(self.config.get('mqtt', 'port', fallback='1833'))
        if not self.config.has_option('mqtt', 'username') or not self.config.has_option('mqtt', 'password'):
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",
                                "Please specify MQTT username and password in the configuration")
        else:
            self.mqtt_username = self.config.get('mqtt', 'username')
            self.mqtt_password = self.config.get('mqtt', 'password')

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
        if self.config.has_option('mqtt', 'discovery_prefix'):
            self.discovery_prefix = self.config.get('mqtt', 'discovery_prefix')
        else:
            self.discovery_prefix = "homeassistant"
        # use the configured device name or the device name from the omnik portal
        if self.config.has_option('mqtt', 'device_name'):
            self.device_name = self.config.get('mqtt', 'device_name')
        else:
            self.device_name = None
        # current_power
        if self.config.has_option('mqtt', 'current_power_name'):
            self.current_power_name = self.config.get('mqtt', 'current_power_name')
        else:
            self.current_power_name = 'Current power'
        # total_energy
        if self.config.has_option('mqtt', 'total_energy_name'):
            self.total_energy_name = self.config.get('mqtt', 'total_energy_name')
        else:
            self.total_energy_name = 'Energy total'
        # today_energy
        if self.config.has_option('mqtt', 'today_energy_name'):
            self.today_energy_name = self.config.get('mqtt', 'today_energy_name')
        else:
            self.today_energy_name = 'Energy today'
        # last_update_time
        if self.config.has_option('mqtt', 'last_update_time_name'):
            self.last_update_time_name = self.config.get('mqtt', 'last_update_time_name')
        else:
            self.last_update_time_name = 'Last update'

    def _mqtt_on_connect(client, userdata, flags, rc):
        if rc == 0:
            hybridlogger.ha_log(client.logger, client.hass_api, "INFO", "MQTT connected")
            # subscribe listening (not used)

    def _mqtt_on_disconnect(client, userdata, flags, rc):
        if rc == 0:
            hybridlogger.ha_log(client.logger, client.hass_api, "INFO", "MQTT disconnected")

    def _topics(self, msg):
        topics = {}
        topics['main'] = f"{self.discovery_prefix}/sensor/omnik_{msg['plant_id']}"
        topics['state'] = f"{topics['main']}/state"
        topics['attr'] = f"{topics['main']}/attr"
        topics['config'] = {}
        topics['config']['current_power'] = f"{topics['main']}/{msg['plant_id']}_current_power/config"
        topics['config']['total_energy'] = f"{topics['main']}/{msg['plant_id']}_total_energy/config"
        topics['config']['today_energy'] = f"{topics['main']}/{msg['plant_id']}_today_energy/config"
        topics['config']['last_update_time'] = f"{topics['main']}/{msg['plant_id']}_last_update_time/config"
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
        if self.config.getboolean('mqtt', 'append_plant_id', False):
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
        config_pl = {}
        # current_power
        config_pl['current_power'] = {
            "~": f"{topics['main']}",
            "uniq_id": f"{msg['plant_id']}_current_power",
            "name": f"{self.current_power_name}",
            "stat_t": "~/state",
            "json_attr_t": "~/attr",
            "dev_cla": "power",
            "ic": "mdi:chart-bell-curve",
            "unit_of_meas": "Watt",
            "val_tpl": "{{(value_json.current_power)}}",
            "dev": device_pl
            }

        # total_energy
        config_pl['total_energy'] = {
            "~": f"{topics['main']}",
            "uniq_id": f"{msg['plant_id']}_total_energy",
            "name": f"{self.total_energy_name}",
            "stat_t": "~/state",
            "json_attr_t": "~/attr",
            "ic": "mdi:counter",
            "unit_of_meas": "kWh",
            "val_tpl": "{{((value_json.total_energy)|round(1))}}",
            "dev": device_pl
            }

        # today_energy
        config_pl['today_energy'] = {
            "~": f"{topics['main']}",
            "uniq_id": f"{msg['plant_id']}_today_energy",
            "name": f"{self.today_energy_name}",
            "stat_t": "~/state",
            "json_attr_t": "~/attr",
            "ic": "mdi:counter",
            "unit_of_meas": "kWh",
            "val_tpl": "{{((value_json.today_energy)|round(2))}}",
            "dev": device_pl
            }

        # last_update_time
        config_pl['last_update_time'] = {
            "~": f"{topics['main']}",
            "uniq_id": f"{msg['plant_id']}_last_update_time",
            "name": f"{self.last_update_time_name}",
            "stat_t": "~/state",
            "json_attr_t": "~/attr",
            "ic": "mdi:calendar-clock",
            "dev_cla": "timestamp",
            "val_tpl": "{{value_json.last_update_time | timestamp_local}}",
            "dev": device_pl
            }
        return config_pl

    def _value_payload(self, msg):
        value_pl = {}
        value_pl["last_update_time"] = float(datetime.timestamp(msg['reporttime']))
        value_pl["current_power"] = int(float(msg['current_power']) * 1000)
        value_pl["total_energy"] = float(msg['total_energy'])
        value_pl["today_energy"] = float(msg['today_energy'])
        # value_pl["income"] = float(msg['income'])
        return value_pl

    def _attribute_payload(self, msg):
        attr_pl = {
            "data_logger": msg['data_logger'],
            "inverter": msg['inverter'],
            "plant_id": int(msg['plant_id']),
            "last_update": f"{msg['reporttime'].strftime('%Y-%m-%d')} {msg['reporttime'].strftime('%H:%M:%S')}"
            }
        return attr_pl

    def _publish_config(self, topics, config_pl, entity):
        try:
            # publish config
            if self.mqtt_client.publish(topics['config'][entity], json.dumps(config_pl[entity])):
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Publishing config {json.dumps(config_pl[entity])} \
                                    to {topics['config'][entity]} successful.")
            else:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",
                                    f"Publishing config {json.dumps(config_pl[entity])} \
                                    to {topics['config'][entity]} failed!")
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",
                                f"Unhandled error publishing config for entity {entity}: {e}")

    def _publish_attributes(self, topics, attr_pl):
        try:
            # publish attributes
            if self.mqtt_client.publish(topics['attr'], json.dumps(attr_pl)):
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Publishing attributes {json.dumps(attr_pl)} to \
                                    {topics['attr']} successful.")
            else:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",
                                    f"Publishing attributes {json.dumps(attr_pl)} to \
                                    {topics['attr']} failed!")
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", f"Unhandled error publishing attributes: {e}")

    def _publish_state(self, topics, value_pl):
        try:
            # publish state
            if self.mqtt_client.publish(topics['state'], json.dumps(value_pl)):
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Publishing state {json.dumps(value_pl)} to \
                                    {topics['state']} successful.")
            else:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",
                                    f"Publishing state {json.dumps(value_pl)} to \
                                    {topics['state']} failed!")
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", f"Unhandled error publishing states: {e}")

    def process(self, **args):
        """
        Send data to homeassistant over mqtt
        """
        # Get argument
        msg = args['msg']

        # Set report time in local timezone
        msg['reporttime'] = datetime.strptime(f"{msg['last_update_time']} UTC+0000",
                                              '%Y-%m-%dT%H:%M:%SZ %Z%z').astimezone(self.timezone)
        # Get topics
        topics = self._topics(msg)

        # publish attributes
        attr_pl = self._attribute_payload(msg)
        self._publish_attributes(topics, attr_pl)

        # Publish config
        config_pl = self._config_payload(msg, topics)
        for entity in config_pl:
            self._publish_config(topics, config_pl, entity)

        # publish state
        value_pl = self._value_payload(msg)
        self._publish_state(topics, value_pl)
