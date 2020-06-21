#! /bin/bash
LOCAL_IP="192.168.1.x"
DEST_PORT="10004"
OMNIK_LOGGER_ADDRESS="176.58.117.69"
# Flush existing NAT rules
iptables -t nat -F OUTPUT
iptables -t nat -F PREROUTING
# Set NAT RULES correctly
iptables -t nat -A PREROUTING -p tcp -d $OMNIK_LOGGER_ADDRESS --dport $DEST_PORT -j DNAT --to-destination $LOCAL_IP:$DEST_PORT
iptables -t nat -A OUTPUT -p tcp -d $OMNIK_LOGGER_ADDRESS -j DNAT --to-destination $LOCAL_IP
