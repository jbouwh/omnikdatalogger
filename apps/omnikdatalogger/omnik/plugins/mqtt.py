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
        self.mqtt_client.on_connect = self.mqtt_on_connect  # bind call back function
        self.mqtt_client.on_disconnect = self.mqtt_on_disconnect  # bind call back function
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
        # income
        if self.config.has_option('mqtt', 'income_name'):
            self.income_name = self.config.get('mqtt', 'income_name')
        else:
            self.income_name = 'Income'
        # last_update_time
        if self.config.has_option('mqtt', 'last_update_time_name'):
            self.last_update_time_name = self.config.get('mqtt', 'last_update_time_name')
        else:
            self.last_update_time_name = 'Last update'

    def mqtt_on_connect(client, userdata, flags, rc):
        if rc == 0:
            hybridlogger.ha_log(client.logger, client.hass_api, "INFO", "MQTT connected")
            # subscribe listening (not used)

    def mqtt_on_disconnect(client, userdata, flags, rc):
        if rc == 0:
            hybridlogger.ha_log(client.logger, client.hass_api, "INFO", "MQTT disconnected")

    def process(self, **args):
        """
        Send data to homeassistant over mqtt
        """
        msg = args['msg']
        if not self.device_name:
            self.device_name = msg['name']
        value_pl = {}
        attr_pl = {}
        plant_appendix = ""
        if self.config.getboolean('mqtt', 'append_plant_id', False):
            plant_appendix = f" [{msg['plant_id']}]"
        model = "Omnik data logger"
        main_topic = f"{self.discovery_prefix}/sensor/omnik_{msg['plant_id']}"
        state_topic = f"{main_topic}/state"
        attr_topic = f"{main_topic}/attr"

        reporttime = datetime.strptime(f"{msg['last_update_time']} UTC+0000",
                                       '%Y-%m-%dT%H:%M:%SZ %Z%z').astimezone(self.timezone)
        device_pl = {
            "identifiers": [f"omnik_{msg['plant_id']}"],
            "name": f"{self.device_name}{plant_appendix}",
            "mdl": model,
            "mf": 'Omnik'
            }
        attr_pl = {
            "current_power": int(float(msg['current_power']) * 1000),
            "today_energy": float(msg['today_energy']),
            "monthly_energy": float(msg['monthly_energy']),
            "yearly_energy": float(msg['yearly_energy']),
            "peak_power_actual": float(msg['peak_power_actual']),
            "efficiency": float(msg['efficiency']),
            "plant_id": int(msg['plant_id']),
            "last_update": f"{reporttime.strftime('%Y-%m-%d')} {reporttime.strftime('%H:%M:%S')}"
            }

        # current_power
        current_power_config_topic = f"{main_topic}/{msg['plant_id']}_current_power/config"
        current_power_config_pl = {
            "~": f"{main_topic}",
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
        value_pl["current_power"] = int(float(msg['current_power']) * 1000)

        # total_energy
        total_energy_config_topic = f"{main_topic}/{msg['plant_id']}_total_energy/config"
        total_energy_config_pl = {
            "~": f"{main_topic}",
            "uniq_id": f"{msg['plant_id']}_total_energy",
            "name": f"{self.total_energy_name}",
            "stat_t": "~/state",
            "json_attr_t": "~/attr",
            "ic": "mdi:counter",
            "unit_of_meas": "kWh",
            "val_tpl": "{{((value_json.total_energy)|round(1))}}",
            "dev": device_pl
            }
        value_pl["total_energy"] = float(msg['total_energy'])

        # income
        income_config_topic = f"{main_topic}/{msg['plant_id']}_income/config"
        income_config_pl = {
            "~": f"{main_topic}",
            "uniq_id": f"{msg['plant_id']}_income",
            "name": f"{self.income_name}",
            "stat_t": "~/state",
            "json_attr_t": "~/attr",
            "ic": "mdi:currency-eur",
            "unit_of_meas": "€",
            "val_tpl": "{{((value_json.income)|round(2))}}",
            "dev": device_pl
            }
        value_pl["income"] = float(msg['income'])

        # last_update_time
        last_update_time_config_topic = f"{main_topic}/{msg['plant_id']}_last_update_time/config"
        last_update_time_config_pl = {
            "~": f"{main_topic}",
            "uniq_id": f"{msg['plant_id']}_last_update_time",
            "name": f"{self.last_update_time_name}",
            "stat_t": "~/state",
            "json_attr_t": "~/attr",
            "ic": "mdi:calendar-clock",
            "dev_cla": "timestamp",
            "val_tpl":"{{value_json.last_update_time | timestamp_local}}",
            "dev": device_pl
            }
        value_pl["last_update_time"] = float(datetime.timestamp(reporttime))

        try:
            # publish config
            # current_power
            if self.mqtt_client.publish(current_power_config_topic, json.dumps(current_power_config_pl)):
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Publishing config {json.dumps(current_power_config_pl)} \
                                    to {current_power_config_topic} successful.")
            else:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",
                                    f"Publishing config {json.dumps(current_power_config_pl)} \
                                    to {current_power_config_topic} failed!")
            # total_energy
            if self.mqtt_client.publish(total_energy_config_topic, json.dumps(total_energy_config_pl)):
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Publishing config {json.dumps(total_energy_config_pl)} to \
                                    {total_energy_config_topic} successful.")
            else:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",
                                    f"Publishing config {json.dumps(total_energy_config_pl)} to \
                                    {total_energy_config_topic} failed!")
            # income
            if self.mqtt_client.publish(income_config_topic, json.dumps(income_config_pl)):
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Publishing config {json.dumps(income_config_pl)} to \
                                    {income_config_topic} successful.")
            else:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",
                                    f"Publishing config {json.dumps(income_config_pl)} to \
                                    {income_config_topic} failed!")
            # last_update_time
            if self.mqtt_client.publish(last_update_time_config_topic, json.dumps(last_update_time_config_pl)):
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Publishing config {json.dumps(last_update_time_config_pl)} to \
                                    {last_update_time_config_topic} successful.")
            else:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",
                                    f"Publishing config {json.dumps(last_update_time_config_pl)} to \
                                    {last_update_time_config_topic} failed!")

            # publish attributes
            if self.mqtt_client.publish(attr_topic,json.dumps(attr_pl)):
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Publishing attributes {json.dumps(attr_pl)} to \
                                    {attr_topic} successful.")
            else:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",
                                    f"Publishing attributes {json.dumps(attr_pl)} to \
                                    {attr_topic} failed!")
            # publish state
            if self.mqtt_client.publish(state_topic,json.dumps(value_pl)):
                hybridlogger.ha_log(self.logger, self.hass_api, "DEBUG",
                                    f"Publishing state {json.dumps(value_pl)} to \
                                    {state_topic} successful.")
            else:
                hybridlogger.ha_log(self.logger, self.hass_api, "WARNING",
                                    f"Publishing state {json.dumps(value_pl)} to \
                                    {state_topic} failed!")
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR", e)
