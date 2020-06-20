# OMNIKDATALOGGERPROXY

Use these files to intercept your inverters data messages. See the comments in the example shell script en config.ini about how to use them.
Good luck with them

## Install using pip3
`pip3 install omnikdataloggerproxy`

## Prearing your Synology to run run omnikdatalogger the proxy script (manual install)

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

## Prearing your Synology to run run omnikdatalogger the proxy script

You can use the following systemd config to run the script as a service (The example shows a forwarding only setup)

```service
[Unit]
Description=Omnik datalogger proxy
After=network.target
[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/jbouwh/python/omnikloggerproxy.py --serialnumber NLDN123456789012 --listenaddress 0.0.0.0 --omniklogger 176.58.117.69 --omnikloggerport 10004
User=jbouwh
Group=users
Restart=on-failure
RestartSec=30s
[Install]
WantedBy=multi-user.target
```

To setup as root:
* Update the user and serial number in the script
* Link the script to `/etc/systemd/system/omnikloggerproxy.service`
* Enable the service: `systemctl enable omnikloggerproxy`
* Start the service: `systemctl start omnikloggerproxy`