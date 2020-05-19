#! /usr/bin/python3
import socket
import argparse
import configparser
import threading
import signal
import json
import base64
import os
import paho.mqtt.client as mqttclient
import uuid
import logging
import threading

import datetime
# import pytz

listenaddress = b'127.0.0.1'                        # <<<< change this to your ip address >>>>
listenport = 10004                                 # Make sure your firewall enables you listening at this port
omnikloggerpublicaddress = b'176.58.117.69'         # There is no need to change this if this proxy
                                                   # should direct log your data to the Omnik/SolarmanPV servers
omnikloggerdestport = 10004                        # This is the port the omnik/SolarmanPV datalogger server listens to
STATUS_ON = 'ON'
STATUS_OFF = 'OFF'
CHECK_STATUS_INTERVAL = 60
INVERTER_MAX_IDLE_TIME = 30

global stopflag


#Generic signal handler
def signal_handler(signal, frame):
    global stopflag
    logging.debug("Signal {:0d} received. Setting stopflag.".format(signal))
    stopflag = True

class ProxyServer(threading.Thread):

    def __init__(self, args=[], kwargs={}):
        self.stopsignal=0
        self.sockwait = threading.Event()

        threading.Thread.__init__(self)
        self.data = None
        self.connection = None
        self.sock = None
        if args.mqtt_host:
            self.mqttfw = mqtt(args)
        else:
            self.mqttfw = None
        self.status = {}
        self.lastupdate = {}

        # Check every 60 sec if there is a valid update status aged less than 30 minutes
        self.statustimer = threading.Timer(CHECK_STATUS_INTERVAL, self.check_status)
        self.statustimer.start()


    def check_status(self):
        for serial in self.lastupdate:
            if self.lastupdate[serial] + datetime.timedelta(minutes=INVERTER_MAX_IDLE_TIME) < datetime.datetime.now():
                self.status[serial] = STATUS_OFF
                self.mqttfw.mqttforward(json.dumps(str(base64.b64encode(b'')).encode('UTF-8')), 
                                    serial, self.status[serial])
        # Restart timer
        self.statustimer = threading.Timer(CHECK_STATUS_INTERVAL, self.check_status)
        self.statustimer.start()


    def cancel(self):
        self.stopsignal=1
        try:
            self.statustimer.cancel()
        except:
            pass
        try:
            # Work-a-round to close listening socket
            socket.socket(socket.AF_INET, 
                  socket.SOCK_STREAM).connect(self.server_address)
            self.sock.close()
        except:
            pass
        if self.mqttfw:
            self.mqttfw.close()
        self.sockwait.clear()

    def sockaccept(self):
        # Wait for connection
        try:
            self.connection, self.client_address = self.sock.accept()
            #connection, client_address = self.sock.accept()
            if not self.stopsignal:
                logging.debug('client connected: {0}'.format(self.client_address))
                # Process received data
                self.data = self.connection.recv(1024)
        except:
            pass
        self.sockwait.set()

    def run(self):
        # Try to run TCP server
        # Create a TCP/IP socket to listen
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to the address given on the command line
        self.server_address = (args.listenaddress, args.listenport)
        self.sock.bind(self.server_address)
        logging.info('starting up on %s port %s' % self.sock.getsockname())
        # Accept max 1 connection
        self.sock.listen(1)
        #main loop
        while not self.stopsignal:
            logging.debug('waiting for a connection')

            # Initialize event for handling accept socket
            self.sockwait = threading.Event()
            # Initialize data var
            self.data = None
            self.serial = None

            acceptthread = threading.Thread(target=self.sockaccept)
            # Wait for accept
            acceptthread.start()
            # The following call will block the thead
            self.sockwait.wait()
            if self.connection:
                if self.data and len(self.data)==128:
                    rawserial = str(self.data[15:31].decode())
                    # obj dLog transforms de raw data from the photovoltaic Systems converter
                    valid = False
                    if rawserial in args.serialnumber:
                        self.status[rawserial] = STATUS_ON
                        self.lastupdate[rawserial] = datetime.datetime.now()
                        valid = True
                    if valid:
                        # Process data
                        logging.info("Processing message for inverter '{0}'".format(rawserial))
                        self.forwardstate(rawserial, self.status[rawserial])
                        if self.connection:
                            try:
                                self.connection.sendall(b'')
                            except:
                                pass
                            # give replay if connection is not closed yet
                    else:
                        logging.warning("Received incorrect data, ignoring connection!")
                        continue
                if self.connection:
                    try:
                        self.connection.close()
                        logging.debug('connection closed')
                    except:
                        pass

    def forwardstate(self, serial, status):
        # Forward data to datalogger and MQTT
        # TODO
        # Forward logger message to MTTQ if host is defined
        if self.mqttfw:
            self.mqttfw.mqttforward(json.dumps(str(base64.b64encode(self.data))), 
                                    serial, status)
        # Forward data to proxy or Omnik datalogger
        if args.omniklogger:
            self.fwthread = tcpforward()
            self.fwthread.forward(self.data)
            self.fwthread.join(60)
            if self.fwthread.isAlive():
                # Kill the thread if it is blocking
                self.fwthread.self.raise_exception()

class tcpforward(threading.Thread):
    
    def forward(self, data):
        threading.Thread.__init__(self, target=self._run)
        self.data = data
        self.start()

    def _run(self):
        loggeraddress = (args.omniklogger, int(args.omnikloggerport))
        self.forwardsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.forwardsock.connect(loggeraddress)
            logging.info('{0} Forwarding to omnik logger "{1}"'.format(datetime.datetime.now(), args.omniklogger))
            self.forwardsock.sendall(self.data)
            logging.info('Forwarding succesful.')
        except socket.timeout:
            logging.warning("Timeout error forwarding: {0}".format(e))
        except Exception as e:
            logging.warning("Error forwarding: {0}".format(e))
        finally:
            self.forwardsock.close()

class mqtt(object):

    def __init__(self, args=[], kwargs={}):
        # self.timezone = pytz.timezone(args.timezone)
        self.mqtt_client_name = args.mqtt_client_name_prefix + uuid.uuid4().hex
        self.mqtt_host = args.mqtt_host
        self.mqtt_port = int(args.mqtt_port)
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
        self.logger_sensor_name  = args.mqtt_logger_sensor_name 

    def close(self):
        self.mqtt_client.disconnect()

    def _topics(self):
        topics = {}
        topics['main'] = "{0}/binary_sensor/{1}_{2}".format(self.discovery_prefix, self.device_name, self.serial)
        topics['state'] = "{0}/state".format(topics['main'])
        topics['attr'] =  "{0}/attr".format(topics['main'])
        topics['config'] = {}
        topics['config']['logger_sensor'] = "{0}/logger_sensor/config".format(topics['main'])
        return topics

    def _device_payload(self):
        # Determine model
        model = "Omnik data logger"

        # Device payload
        device_pl = {
            "identifiers": ["{0}_{1}".format(self.device_name, self.serial)],
            "name": "{0}_{1}".format(self.device_name, self.serial),
            "mdl": model,
            "mf": 'Omnik'
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
        value_pl = { "state" : self.status }
        return value_pl

    def _attribute_payload(self):
        attr_pl = {
            "inverter": self.serial,
            "data": self.data,
            "last_update": "{0} {1}".format(self.reporttime.strftime('%Y-%m-%d'), self.reporttime.strftime('%H:%M:%S'))
            }
        return attr_pl

    def _publish_config(self, topics, config_pl, entity):
        try:
            # publish config
            if self.mqtt_client.publish(topics['config'][entity], json.dumps(config_pl[entity])):
                logging.debug("Publishing config {0} successful.".format(entity))
            else:
                logging.warning("Publishing config {0} failed!".format(entity))
        except Exception as e:
            logging.error("Unhandled error publishing config for entity {entity}: {0}".format(e))

    def _publish_attributes(self, topics, attr_pl):
        try:
            # publish attributes
            if self.mqtt_client.publish(topics['attr'], json.dumps(attr_pl)):
                logging.debug("Publishing attributes successful.")
            else:
                logging.warning("Publishing attributes failed!")
        except Exception as e:
            logging.error("Unhandled error publishing attributes: {0}".format(e))

    def _publish_state(self, topics, value_pl):
        try:
            # publish state
            if self.mqtt_client.publish(topics['state'], json.dumps(value_pl)):
                logging.debug("Publishing state {0} successful.".format(json.dumps(value_pl)))
            else:
                logging.warning("Publishing state {0} failed!".format(json.dumps(value_pl)))
        except Exception as e:
            logging.error("Unhandled error publishing states: {0}".format(e))

    def mqttforward(self, data, serial, status):
        # Decode data: base64.b64decode(json.loads(d, encoding='UTF-8'))
        # Set report time in local timezone
        self.data = data
        self.serial = serial
        self.status = status
        self.reporttime = datetime.datetime.now()
        # Get topics
        topics = self._topics()

        logging.debug("{0} Forwarding message to MQTT service".format(self.reporttime))
        # publish attributes
        attr_pl = self._attribute_payload()
        self._publish_attributes(topics, attr_pl)

        # Publish config
        config_pl = self._config_payload(topics)
        for entity in config_pl:
            self._publish_config(topics, config_pl, entity)

        # publish state
        value_pl = self._value_payload()
        self._publish_state(topics, value_pl)

    def _mqtt_on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("MQTT connected")
            # subscribe listening (not used)

    def _mqtt_on_disconnect(client, userdata, flags, rc):
        if rc == 0:
            logging.info("MQTT disconnected")

def main(args):
    global stopflag
    signal.signal(signal.SIGINT, signal_handler)
    proxy=ProxyServer(args)
    proxy.start()
    try:
        while not stopflag:
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
                        help='Forward to an address omnik/SolarmanPV datalogger server listens to. Set this to {0} as final forwarder.'.format(omnikloggerpublicaddress))
    parser.add_argument('--omnikloggerport', default=omnikloggerdestport,
                        help='The port the omnik/SolarmanPV datalogger server listens to')
    parser.add_argument('--mqtt_host', default=None,
                        help='The mqtt host to forward processed data to. Config overrides.')
    parser.add_argument('--mqtt_port', default='1883',
                        help='The mqtt server port. Config overrides.')
    parser.add_argument('--mqtt_discovery_prefix', default='homeassistant',
                        help='The mqtt topoc prefix (used for MQTT auto discovery). Config overrides.')
    parser.add_argument('--mqtt_client_name_prefix', default='ha-mqtt-omnikloggerproxy',
                        help='The port the omnik/SolarmanPV datalogger server listens to. Config overrides.')
    parser.add_argument('--mqtt_username', default=None,
                        help='The mqtt username. Config overrides.')
    parser.add_argument('--mqtt_password', default=None,
                        help='The mqtt password. Config overrides.')
    parser.add_argument('--mqtt_device_name', default='Omnik',
                        help='The device name that apears using mqtt autodiscovery (HA). Config overrides.')
    parser.add_argument('--mqtt_logger_sensor_name', default='Datalogger',
                        help='The device name that apears using mqtt autodiscovery (HA). Config overrides.')
    parser.add_argument('--timezone', default='Europe/Amsterdam',
                        help='The local time zone (for tzdata). Config overrides.')
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
        args.mqtt_host = c.get('mqtt','host', fallback=args.mqtt_host)
        args.mqtt_port = c.get('mqtt','port', fallback=args.mqtt_port)
        args.mqtt_discovery_prefix = c.get('mqtt','discovery_prefix ', fallback=args.mqtt_discovery_prefix)
        args.mqtt_client_name_prefix = c.get('mqtt','client_name_prefix', fallback=args.mqtt_client_name_prefix)
        args.mqtt_username = c.get('mqtt', 'username', fallback=args.mqtt_username)
        args.mqtt_password = c.get('mqtt', 'password', fallback=args.mqtt_password)
        args.mqtt_device_name = c.get('mqtt','device_name', fallback=args.mqtt_device_name)
        args.mqtt_device_name = c.get('mqtt','logger_sensor_name', fallback=args.mqtt_logger_sensor_name)
        args.timezone = c.get('default','timezone',  fallback=args.timezone)
        
    main(args)
