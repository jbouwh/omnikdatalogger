#! /bin/bash

# This script configures Network Address Translation using iptables
# At startup existing NAT rules will be reset first
# At yoyr Internet modem/gateway, you need to install a static roue to the IP-address of the device where this script is executed
# Use the config.ini file (see example) to configure MQTT forwarding to your MQTT-server (or Home Assistan environment)
# Execute this script at startup
# This script was tested with Synology DSM 6.2.3 on a Synology DS128 play
# Place this script on a save place together with config.ini file 

LOCAL_IP="192.168.1.1"
DEST_PORT="10004"

LISTEN_ADDRESS="0.0.0.0"

OMNIK_LOGGER_ADDRESS="176.58.117.69"
SERIAL_NUMBER="NLDN123456789012"

FORWARD_ADDRESS="fqdn.example.com""

cd "$(dirname "$0")"

# Flush existing NAT rules
iptables -t nat -F OUTPUT
iptables -t nat -F PREROUTING
# Set NAT RULES correctly
iptables -t nat -A PREROUTING -p tcp -d $OMNIK_LOGGER_ADDRESS --dport $DEST_PORT -j DNAT --to-destination $LOCAL_IP:$DEST_PORT
iptables -t nat -A OUTPUT -p tcp -d $OMNIK_LOGGER_ADDRESS -j DNAT --to-destination $LOCAL_IP

# Start TCP proxy for OMNIK logger
python3 ./omnikloggerproxy.py --config config.ini --listenaddress $LISTEN_ADDRESS --omniklogger $FORWARD_ADDRESS --serialnumber $SERIAL_NUMBER
