#! /usr/bin/env python
#
# This script can be used to intercept and forward the inverter log messages.
# The script has been tested with python versions 2.7 and 3.8
# The data can be forwarded to MQTT to process using omnikdatalogger with the halogger client.
# To intercept on your local network:
# Route 176.58.117.69/32 to the device that runs this logger and listen at port 10004
# On the device NAT the poblic address to the private address (e.g. 192.168.x.x ) using iptables:
# iptables -t nat -A PREROUTING -p tcp -d 176.58.117.69 --dport 10004 -j DNAT --to-destination 192.168.x.x:10004
# iptables -t nat -A OUTPUT -p tcp -d 176.58.117.69 -j DNAT --to-destination 192.168.x.x
#

import socket
import socketserver
import argparse
import configparser
import threading
import signal
import json
import binascii
import os
import paho.mqtt.client as mqttclient
import uuid
import logging
import datetime
import time

__version__ = '1.1.2'
listenaddress = b'127.0.0.1'                       # <<<< change this to your ip address >>>>
listenport = 10004                                 # Make sure your firewall enables you listening at this port
# There is no need to change this if this proxy must log your data directly to the Omnik/SolarmanPV servers
omnikloggerpublicaddress = b'176.58.117.69'        # There is no need to change this if this proxy
omnikloggerdestport = 10004                        # This is the port the omnik/SolarmanPV datalogger server listens to
STATUS_ON = 'ON'
STATUS_OFF = 'OFF'
CHECK_STATUS_INTERVAL = 60
INVERTER_MAX_IDLE_TIME = 10

global stopflag


# Generic signal handler
def signal_handler(signal, frame):
    global stopflag
    logging.debug("Signal {:0d} received. Setting stopflag.".format(signal))
    stopflag = True


class ProxyServer(threading.Thread):

    def __init__(self, args=[], kwargs={}):
        threading.Thread.__init__(self)
        if args.mqtt_host:
            logging.info('Enabling MQTT forward to {0}'.format(args.mqtt_host))
            RequestHandler.mqttfw = mqtt(args)
            # Check every 60 sec if there is a valid update status aged less than 30 minutes
            self.statustimer = threading.Timer(CHECK_STATUS_INTERVAL, self.check_status)
            self.statustimer.start()

        # Create tcp server
        self.tcpServer = socketserver.TCPServer((args.listenaddress, args.listenport), RequestHandler)

    def check_status(self):
        for serial in RequestHandler.lastupdate:
            if RequestHandler.lastupdate[serial] + datetime.timedelta(minutes=INVERTER_MAX_IDLE_TIME) < \
                    datetime.datetime.now():
                RequestHandler.status[serial] = STATUS_OFF
                RequestHandler.mqttfw.mqttforward('',
                                                  serial, self.status[serial])
        # Restart timer
        self.statustimer = threading.Timer(CHECK_STATUS_INTERVAL, self.check_status)
        self.statustimer.start()

    def cancel(self):
        # Stop the loop
        self.tcpServer.shutdown()
        if RequestHandler.mqttfw:
            self.statustimer.cancel()
            RequestHandler.mqttfw.close()

    def run(self):
        # Try to run TCP server
        logging.info('Start in Omnik proxy server. Listening to {0}:{1}'.format(args.listenaddress, args.listenport))
        self.tcpServer.serve_forever()


class RequestHandler(socketserver.BaseRequestHandler):

    mqttfw = None
    status = {}
    lastupdate = {}

    def handle(self):
        msg = self.request.recv(1024)

        if len(msg) >= 99:
            self._processmsg(msg)

    def _processmsg(self, msg):
        rawserial = str(msg[15:31].decode())
        # obj dLog transforms de raw data from the photovoltaic Systems converter
        valid = False
        if rawserial in args.serialnumber:
            # TODO: Dit gaat niet werken zo
            RequestHandler.status[rawserial] = STATUS_ON
            RequestHandler.lastupdate[rawserial] = datetime.datetime.now()
            valid = True
        if valid:
            # Process data
            logging.info("Processing message for inverter '{0}'".format(rawserial))
            self.forwardstate(msg, rawserial, self.status[rawserial])
        else:
            logging.warning("Ignoring received data!")

    def forwardstate(self, msg, serial, status):
        # Forward data to datalogger and MQTT
        # TODO
        # Forward logger message to MTTQ if host is defined
        if RequestHandler.mqttfw:
            RequestHandler.mqttfw.mqttforward(json.dumps(str(binascii.b2a_base64(msg), encoding='ascii')),
                                              serial, status)
        # Forward data to proxy or Omnik datalogger
        if args.omniklogger:
            self.fwthread = tcpforward()
            self.fwthread.forward(msg)
            self.fwthread.join(60)
            if self.fwthread.isAlive():
                # Kill the thread if it is still blocking
                logging.warning("Waiting for forward connection takes a long time...")
                self.fwthread.join()


class tcpforward(threading.Thread):

    def forward(self, data):
        threading.Thread.__init__(self, target=self._run)
        self.data = data
        self.start()

    def _run(self):
        loggeraddress = (args.omniklogger, int(args.omnikloggerport))
        self.forwardsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.forwardsock.settimeout(90)
        try:
            self.forwardsock.connect(loggeraddress)
            self.forwardsock.sendall(self.data)
            logging.info('{0} Forwarded to "{1}"'.format(datetime.datetime.now(), args.omniklogger))
            self.forwardsock.close()
        except Exception as e:
            logging.warning("Error forwarding: {0}".format(e))
        finally:
            self.forwardsock.close()


class mqtt(object):

    def __init__(self, args=[], kwargs={}):
        self.mqtt_client_name = args.mqtt_client_name_prefix + uuid.uuid4().hex
        self.mqtt_host = args.mqtt_host
        self.mqtt_port = int(args.mqtt_port)
        self.mqtt_retain = args.mqtt_retain
        if not args.mqtt_username or not args.mqtt_password:
            logging.error("Please specify MQTT username and password in the configuration")
            return
        else:
            self.mqtt_username = args.mqtt_username
            self.mqtt_password = args.mqtt_password

        # mqtt setup
        self.mqtt_client = mqttclient.Client(self.mqtt_client_name)
        self.mqtt_client.on_connect = self._mqtt_on_connect  # bind call back function
        self.mqtt_client.on_disconnect = self._mqtt_on_disconnect  # bind call back function
        # self.mqtt_client.on_message=mqtt_on_message (not used)
        self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
        self.mqtt_client.connect(self.mqtt_host, self.mqtt_port)
        # start processing messages
        self.mqtt_client.loop_start()
        # default prefixes
        self.discovery_prefix = args.mqtt_discovery_prefix
        self.device_name = args.mqtt_device_name
        self.logger_sensor_name = args.mqtt_logger_sensor_name

        # lock
        self.lock = threading.Condition(threading.Lock())

    def close(self):
        self.mqtt_client.disconnect()

    def _topics(self):
        topics = {}
        topics['main'] = "{0}/binary_sensor/{1}_{2}".format(self.discovery_prefix, self.logger_sensor_name, self.serial)
        topics['state'] = "{0}/state".format(topics['main'])
        topics['attr'] = "{0}/attr".format(topics['main'])
        topics['config'] = {}
        topics['config']['logger_sensor'] = "{0}/logger_sensor/config".format(topics['main'])
        return topics

    def _device_payload(self):
        # Determine model
        model = "Omnik datalogger proxy"

        # Device payload
        device_pl = {
            "identifiers": ["{0}_{1}".format(self.device_name, self.serial)],
            "name": "{0}_{1}".format(self.device_name, self.serial),
            "mdl": model,
            "mf": 'JBsoft',
            "sw": __version__
            }
        return device_pl

    def _config_payload(self, topics):
        # Get device payload
        device_pl = self._device_payload()
        # Fill config_pl dict
        config_pl = {}
        # current_power
        config_pl['logger_sensor'] = {
            "~": "{0}".format(topics['main']),
            "uniq_id": "{0}_{1}_logger".format(self.device_name, self.serial),
            "name": "{0}".format(self.logger_sensor_name),
            "stat_t": "~/state",
            "json_attr_t": "~/attr",
            "dev_cla": "power",
            "val_tpl": "{{ value_json.state }}",
            "dev": device_pl
            }
        return config_pl

    def _value_payload(self):
        value_pl = {"state": self.status}
        return value_pl

    def _attribute_payload(self):
        attr_pl = {
            "inverter": self.serial,
            "data": self.data,
            "timestamp": time.time(),
            "last_update": "{0} {1}".format(self.reporttime.strftime('%Y-%m-%d'), self.reporttime.strftime('%H:%M:%S'))
            }
        return attr_pl

    def _publish_config(self, topics, config_pl, entity):
        try:
            # publish config
            if self.mqtt_client.publish(topics['config'][entity], json.dumps(config_pl[entity]), retain=self.mqtt_retain):
                logging.debug("Publishing config {0} successful.".format(entity))
                return True
            else:
                logging.warning("Publishing config {0} failed!".format(entity))
                return False
        except Exception as e:
            logging.error("Unhandled error publishing config for entity {0}: {1}".format(entity, e))
            return False

    def _publish_attributes(self, topics, attr_pl):
        try:
            # publish attributes
            if self.mqtt_client.publish(topics['attr'], json.dumps(attr_pl), retain=self.mqtt_retain):
                logging.debug("Publishing attributes successful.")
                return True
            else:
                logging.warning("Publishing attributes failed!")
                return False
        except Exception as e:
            logging.error("Unhandled error publishing attributes: {0}".format(e))
            return False

    def _publish_state(self, topics, value_pl):
        try:
            # publish state
            if self.mqtt_client.publish(topics['state'], json.dumps(value_pl), retain=self.mqtt_retain):
                logging.debug("Publishing state {0} successful.".format(json.dumps(value_pl)))
                return True
            else:
                logging.warning("Publishing state {0} failed!".format(json.dumps(value_pl)))
                return False
        except Exception as e:
            logging.error("Unhandled error publishing states: {0}".format(e))
            return False

    def mqttforward(self, data, serial, status):
        # Decode data: base64.b64decode(json.loads(d, encoding='UTF-8'))
        self.lock.acquire()
        self.data = data
        self.serial = serial
        self.status = status
        self.reporttime = datetime.datetime.now()
        # Get topics
        topics = self._topics()
        # publish attributes
        attr_pl = self._attribute_payload()
        self._publish_attributes(topics, attr_pl)

        # Publish config
        config_pl = self._config_payload(topics)
        for entity in config_pl:
            self._publish_config(topics, config_pl, entity)

        # publish state
        value_pl = self._value_payload()
        if self._publish_state(topics, value_pl):
            logging.info('{0} Message forwarded to MQTT service at "{1}"'.format(datetime.datetime.now(), args.mqtt_host))

        self.lock.release()

    def _mqtt_on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("MQTT connected")
            # subscribe listening (not used)

    def _mqtt_on_disconnect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("MQTT disconnected")


def main(args):
    global stopflag
    signal.signal(signal.SIGINT, signal_handler)
    proxy = ProxyServer(args)
    proxy.start()
    try:
        while not stopflag and proxy.isAlive():
            proxy.join(1)
    except KeyboardInterrupt:
        pass
    proxy.cancel()
    logging.info("Stopping threads...")
    proxy.join()


if __name__ == '__main__':
    stopflag = False
    home = os.path.expanduser('~')

    parser = argparse.ArgumentParser()
    parser.add_argument('--serialnumber', default=None, nargs='+', required=True,
                        help='The serial number(s) of your inverter')
    parser.add_argument('--config', default=os.path.join(home, '.omnik/config.ini'),
                        help='The config file')
    parser.add_argument('--loglevel', default='INFO',
                        help='The basic loglevel [DEBUG, INFO, WARNING, ERROR, CRITICAL]')
    parser.add_argument('--listenaddress', default=listenaddress,
                        help='A local available address to listen to')
    parser.add_argument('--listenport', default=listenport, type=int,
                        help='The local port to listen to')
    parser.add_argument('--omniklogger', default=None,
                        help='Forward to an address omnik/SolarmanPV datalogger server listens to. '
                             'Set this to {0} as final forwarder.'.format(omnikloggerpublicaddress))
    parser.add_argument('--omnikloggerport', default=omnikloggerdestport,
                        help='The port the omnik/SolarmanPV datalogger server listens to')
    parser.add_argument('--mqtt_host', default=None,
                        help='The mqtt host to forward processed data to. Config overrides.')
    parser.add_argument('--mqtt_port', default='1883',
                        help='The mqtt server port. Config overrides.')
    parser.add_argument('--mqtt_retain', default=True, type=bool,
                        help='The mqtt data message retains. Config overrides.')
    parser.add_argument('--mqtt_discovery_prefix', default='homeassistant',
                        help='The mqtt topoc prefix (used for MQTT auto discovery). Config overrides.')
    parser.add_argument('--mqtt_client_name_prefix', default='ha-mqtt-omnikloggerproxy',
                        help='The port the omnik/SolarmanPV datalogger server listens to. Config overrides.')
    parser.add_argument('--mqtt_username', default=None,
                        help='The mqtt username. Config overrides.')
    parser.add_argument('--mqtt_password', default=None,
                        help='The mqtt password. Config overrides.')
    parser.add_argument('--mqtt_device_name', default='Datalogger proxy',
                        help='The device name that apears using mqtt autodiscovery (HA). Config overrides.')
    parser.add_argument('--mqtt_logger_sensor_name', default='Datalogger',
                        help='The name of data sensor using mqtt autodiscovery (HA). Config overrides.')
    args = parser.parse_args()
    FORMAT = '%(module)s: %(message)s'
    loglevel = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
        }
    logging.basicConfig(level=loglevel[args.loglevel], format=FORMAT)

    if args.config:
        c = configparser.ConfigParser(converters={'list': lambda x: [i.strip() for i in x.split(',')]})
        c.read([args.config], encoding='utf-8')
        args.mqtt_host = c.get('output.mqtt', 'host', fallback=args.mqtt_host)
        args.mqtt_port = c.get('output.mqtt', 'port', fallback=args.mqtt_port)
        args.mqtt_retain = True if c.get('output.mqtt', 'retain', fallback='true') == 'true' else args.mqtt_retain
        args.mqtt_discovery_prefix = c.get('output.mqtt', 'discovery_prefix ', fallback=args.mqtt_discovery_prefix)
        args.mqtt_client_name_prefix = c.get('output.mqtt', 'client_name_prefix', fallback=args.mqtt_client_name_prefix)
        args.mqtt_username = c.get('output.mqtt', 'username', fallback=args.mqtt_username)
        args.mqtt_password = c.get('output.mqtt', 'password', fallback=args.mqtt_password)
        args.mqtt_device_name = c.get('output.mqtt', 'device_name', fallback=args.mqtt_device_name)
        args.logger_sensor_name = c.get('output.mqtt', 'logger_sensor_name', fallback=args.mqtt_logger_sensor_name)

    main(args)
