from omnik.ha_logger import hybridlogger
from omnik.plugin_localproxy import LocalProxyPlugin
import binascii


class HASSAPI(LocalProxyPlugin):

    '''
    This plugin enables you to subscribe to the logger requests using the AppDaemon HASSAPI integration
    Use scripts/proxy/omnikloggerproxy.py to capture the inverter events and publish the data to MQTT (Home Assistant)

    This class makes use the following localproxy client objects
    self.client.msg
    self.client.msgevent
    self.client.semaphore
    self.client.inverters
    self.client.plant_id_list
    '''

    def __init__(self):
        super().__init__()
        hybridlogger.ha_log(self.logger, self.hass_api, "INFO", "localproxy client plugin: HASSAPI")
        self.hass_handle = None
        if not self.hass_api:
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "ERROR", "No HassAPI detected. Use AppDaemon with Home Assistent for this plugin")
            return
        self.logger_entity = self.config.get('client.localproxy.hassapi', 'logger_entity', 'binary_sensor.datalogger')

    def terminate(self):
        if self.hass_handle:
            self.hass_api.cancel_listen_state(self.hass_handle)

    def listen(self):
        if self.hass_api:
            self.hass_handle = self.hass_api.listen_state(self._run, self.logger_entity, attribute='data')
            hybridlogger.ha_log(self.logger, self.hass_api,
                                "INFO", f"HASSapi listening to. '{self.logger_entity}', attribute: 'data'")

    def _run(self, entity, attribute, old, new, kwargs):
        # HASSAPI callback handler
        hybridlogger.ha_log(self.logger, self.hass_api,
                            "INFO",
                            f"HASSapi state change for {self.hass_api.get_state(self.logger_entity, 'inverter', 'n/a')} "
                            f"at {self.hass_api.get_state(self.logger_entity, 'last_update', 'n/a')}")
        # Try to parse payload as json
        try:
            data = binascii.a2b_base64(new)
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
            hybridlogger.ha_log(self.logger, self.hass_api, "WARNING", f"HASSapi: invalid data received: {new}. Error {e}")
