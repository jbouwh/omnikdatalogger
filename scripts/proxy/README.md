# OMNIKDATALOGGERPROXY
![omnikdatalogger](https://github.com/jbouwh/omnikdatalogger/workflows/omnikdatalogger/badge.svg)
![PyPI version](https://badge.fury.io/py/omnikdataloggerproxy.svg) 

The `omnikdataloggerproxy.py` script and supporting files can be used intercept your inverters data messages. See the comments in the example shell script enand the config.ini example about how to use them.
Good luck with them.
The output can be processed with [omnikdatalogger](https://github.com/jbouwh/omnikdatalogger) for output to pvoutput, mqtt, influxdb and integration with Home Assistant.

## Install using pip
`sudo pip3 install omnikdataloggerproxy`

The supporting files are installed at the folder */usr/local/share/omnikdataloggerproxy/*

### Command line
```
usage: omnikloggerproxy.py [-h] --serialnumber SERIALNUMBER [SERIALNUMBER ...]
                           [--config CONFIG] [--loglevel LOGLEVEL]
                           [--listenaddress LISTENADDRESS]
                           [--listenport LISTENPORT]
                           [--omniklogger OMNIKLOGGER]
                           [--omnikloggerport OMNIKLOGGERPORT]
                           [--mqtt_host MQTT_HOST] [--mqtt_port MQTT_PORT]
                           [--mqtt_retain MQTT_RETAIN]
                           [--mqtt_discovery_prefix MQTT_DISCOVERY_PREFIX]
                           [--mqtt_client_name_prefix MQTT_CLIENT_NAME_PREFIX]
                           [--mqtt_username MQTT_USERNAME]
                           [--mqtt_password MQTT_PASSWORD]
                           [--mqtt_device_name MQTT_DEVICE_NAME]
                           [--mqtt_logger_sensor_name MQTT_LOGGER_SENSOR_NAME]
```
### Configuration file
The MQTT parameters will fallback to the `config.ini` settings in the section [output.mqtt]. Specify a configfile using the --config option.
For details see the [Omnik Data Logger README.md](https://github.com/jbouwh/omnikdatalogger#mqtt-settings-under-outputmqtt-in-appsyaml-or-outputmqtt-in-configini-configuration-options)

## Using the proxy script with Synology

### Prearing your Synology to run run omnikdatalogger the proxy script (manual install)

* Make sure you have shell access (ssh or telnet).
* Install pip: `curl -k https://bootstrap.pypa.io/get-pip.py | python3` See: (https://stackoverflow.com/questions/47649902/installing-pip-on-a-dsm-synology)
* Install the paho mqtt client: `/volume1/@appstore/py3k/usr/local/bin/pip3 install paho-mqtt`. The path may be diferent. I used a Synology DS218 play

On upgrades it might be neccesare to reïnstall pip and paho-mqtt. Make sure you chack on this after an update for your Synology.

Now take the following steps:
* Place the omnikloggerproxy.py script, the bash script (omnikproxy_example_startup.sh) and `config.ini_example.txt` to a folder that will not be affected by upgrades. E.g. `/volume1/someshare/yourscriptfolder`.
* Rename `config.ini_example.txt` to `config.ini` and configure settings.
* check the commandline settings in the shell script.
* Try to execute the script to test if it is working. (You can use task plannel later to start the script at boot automatically as activated task)
* The lines to configure iptables should run as root. The omnikproxylogger script works at userlevel too.
* On your internet router/gateway, set up a static route for `176.58.117.69/32` to your synology.
* Configure MQTT to forward the data to be able to use the localproxy plugin with `hassapi` or `mqtt_proxy`.

You can forward the logger trafic to the omnik servers, but if you rerouted yhe traffic for 176.58.117.69 you need to forward to a linux server elswere in the internet.

### Running omnikdataloggerproxy as a service on a Debian based system

You can find the following sample config at `/usr/local/share/omnikdataloggerproxy/omnikdatalogggerproxy.config` after installing `pip3 install omnikdataloggerproxy` as root.

```ini
[Unit]
Description=Omnik datalogger proxy
After=network.target
[Service]
Type=simple
ExecStart=/usr/local/bin/omnikloggerproxy.py --serialnumber NLDN123456789012 --listenaddress 0.0.0.0 --omniklogger 176.58.117.69 --omnikloggerport 10004
User=jbouwh
Group=users
Restart=on-failure
RestartSec=30s
[Install]
WantedBy=multi-user.target
```
The template service file shows a forwarding only setup.

To setup omnikdatalogger proxy as root do:
- Create a config folder and copy the sample service script:
  - `cd /etc/`
  - `mkdir omnikdataloggerproxy`
  - `cp /usr/local/share/omnikdataloggerproxy/omnikdatalogggerproxy.config .`
- Update `User` and *serialnumber* in the script `omnikdatalogggerproxy.config` using your favorite editor.
  - `nano omnikdatalogggerproxy.config`
- Link the script to systemd: to `ln -s /etc/omnikdataloggerproxy/omnikdatalogggerproxy.service /etc/systemd/system/omnikdatalogggerproxy.service`
- Enable the service: `systemctl enable omnikdatalogggerproxy`
- Start the service: `systemctl start omnikdatalogggerproxy`
- check if the service is running: `systemctl status omnikdatalogggerproxy`

After some time the logging should show something similar like this:
```
# systemctl status omnikdataloggerproxy
● omnikdataloggerproxy.service - Omnik datalogger proxy
   Loaded: loaded (/etc/omnikdataloggerproxy/omnikdataloggerproxy.service; enabled; vendor preset: enabled)
   Active: active (running) since Sun 2020-06-21 13:33:21 CEST; 16min ago
 Main PID: 28182 (omnikloggerprox)
    Tasks: 4 (limit: 4915)
   Memory: 9.8M
   CGroup: /system.slice/omnikdataloggerproxy.service
           └─28182 /usr/bin/python3 /usr/local/bin/omnikloggerproxy.py --serialnumber NLDN123456789012 --listenaddress 0.0.0.0 --omniklogger 176.58.117.69 --omnikloggerport 10004

Jun 21 13:33:22 alpha omnikloggerproxy.py[28182]: omnikloggerproxy: Forwarding succesful.
Jun 21 13:38:33 alpha omnikloggerproxy.py[28182]: omnikloggerproxy: Processing message for inverter 'NLDN123456789012'
Jun 21 13:38:33 alpha omnikloggerproxy.py[28182]: omnikloggerproxy: 2020-06-21 13:38:33.795477 Forwarding to omnik logger "176.58.117.69"
Jun 21 13:38:33 alpha omnikloggerproxy.py[28182]: omnikloggerproxy: Forwarding succesful.
Jun 21 13:43:38 alpha omnikloggerproxy.py[28182]: omnikloggerproxy: Processing message for inverter 'NLDN123456789012'
Jun 21 13:43:38 alpha omnikloggerproxy.py[28182]: omnikloggerproxy: 2020-06-21 13:43:38.937148 Forwarding to omnik logger "176.58.117.69"
Jun 21 13:43:38 alpha omnikloggerproxy.py[28182]: omnikloggerproxy: Forwarding succesful.
Jun 21 13:48:50 alpha omnikloggerproxy.py[28182]: omnikloggerproxy: Processing message for inverter 'NLDN123456789012'
Jun 21 13:48:50 alpha omnikloggerproxy.py[28182]: omnikloggerproxy: 2020-06-21 13:48:50.194599 Forwarding to omnik logger "176.58.117.69"
Jun 21 13:48:50 alpha omnikloggerproxy.py[28182]: omnikloggerproxy: Forwarding succesful.
```
The log shows when messages were forwarded.