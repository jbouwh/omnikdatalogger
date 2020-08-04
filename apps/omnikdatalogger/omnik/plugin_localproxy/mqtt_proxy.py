from omnik.ha_logger import hybridlogger
from omnik.plugin_localproxy import LocalProxyPlugin
import paho.mqtt.client as mqttclient
import uuid
import json
import binascii


class MQTTproxy(LocalProxyPlugin):

    '''
    This plugin enables you to subscribe to the logger requests using MQTT
    Use scripts/proxy/omnikloggerproxy.py to capture the inverter events and publish the data to MQTT
    If you are using Home Assistant consider a setup with AppDaemon and the hassapi plugin to collect the published data

    This class makes use the following localproxy client objects
    self.client.msg
    self.client.msgevent
    self.client.semaphore
    self.client.inverters
    self.client.plant_id_list
    '''

    def __init__(self):
        super().__init__()
        hybridlogger.ha_log(self.logger, self.hass_api, "INFO", "localproxy client plugin: MQTTproxy")
        self.logger_sensor_name = self.mqttconfig('logger_sensor_name', 'Datalogger')
        self.mqtt_discovery_prefix = self.mqttconfig('listen_address', 'homeassistant')
        self.mqtt_host = self.mqttconfig('host', 'localhost')
        self.mqtt_port = int(self.mqttconfig('port', '1883'))
        self.mqtt_client_name_prefix = self.mqttconfig('client_name_prefix', 'ha-mqttproxy-omniklogger')
        self.mqtt_client_name = self.mqtt_client_name_prefix + "_" + uuid.uuid4().hex
        self.mqtt_username = self.mqttconfig('username', None)
        self.mqtt_password = self.mqttconfig('password', None)
        if not self.mqtt_username or not self.mqtt_password:
            hybridlogger.ha_log(self.logger, self.hass_api, "ERROR",
                                "Please specify MQTT username and password in the configuration")
        # mqtt setup
        self.mqtt_client = mqttclient.Client(self.mqtt_client_name)
        self.mqtt_client.on_connect = self._mqtt_on_connect  # bind call back function
        self.mqtt_client.on_disconnect = self._mqtt_on_disconnect  # bind call back function
        self.mqtt_client.on_message = self._mqtt_on_message  # called on receiving updates on subscibed messages
        self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)

    def _mqtt_on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO", "MQTTproxy client connected")
            # subscribe to datalogger objects
            for inverter in self.client.inverters:
                topic = f"{self.mqtt_discovery_prefix}/binary_sensor/{self.logger_sensor_name}_"\
                        f"{self.client.inverters[inverter]['inverter_sn']}/attr"
                try:
                    self.mqtt_client.subscribe(topic)
                    hybridlogger.ha_log(self.logger, self.hass_api,
                                        "INFO", f"MQTTproxy subscribed on topic: {topic}")
                except Exception as e:
                    hybridlogger.ha_log(self.logger, self.hass_api,
                                        "ERROR", f"MQTTproxy failed to subsrcibed ontopic: {topic}. Error {e}")

    def _mqtt_on_disconnect(self, client, userdata, flags, rc):
        if rc == 0:
            hybridlogger.ha_log(self.logger, self.hass_api, "INFO", "MQTT disconnected")

    def _mqtt_on_message(self, client, userdata, message):
        # Try to parse payload as json
        try:
            payload = json.loads(message.payload)
            data = binascii.a2b_base64(payload['data'])
            if len(data) == 128:
                # Fill data structure
                self.client.semaphore.acquire()
                self.client.msg['data'] = data
                self.client.msg['isSet'] = True
                self.client.msg['plugin'] = __name__
                self.client.semaphore.release()
                # Trigger processing the message
                self.client.msgevent.set()
        except Exception as e:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "WARNING", f"MQTTproxy: invalid data received on topic: {message.topic}. Error {e}")

    def mqttconfig(self, parameter, fallback):
        return self.config.get('client.localproxy.mqtt_proxy', parameter,
                               self.config.get('output.mqtt', parameter, fallback=fallback))

    def terminate(self):
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()

    def listen(self):
        self.mqtt_client.connect(self.mqtt_host, self.mqtt_port)
        # start processing messages
        self.mqtt_client.loop_start()
