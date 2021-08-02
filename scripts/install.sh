#!/bin/bash

FMSG="- HIAS MQTT BLE Agent installation terminated"

echo "This script will install the HIAS MQTT BLE Agent on your device."
read -p "Proceed (y/n)? " proceed

if [ "$proceed" = "Y" -o "$proceed" = "y" ]; then
    echo "- Installing HIAS MQTT BLE Agent"
    pip3 install --user bcrypt
    pip3 install --user flask
    pip3 install --user paho-mqtt
    pip3 install --user psutil
    pip3 install --user requests
    pip3 install --user web3
    pip3 install --user bluepy
    echo "- HIAS MQTT BLE Agent installed!"
else
    echo $FMSG;
    exit
fi