#!/bin/bash

FMSG="- HIAS MQTT BLE Agent service installation terminated"

echo "This script will install the HIAS MQTT BLE Agent service on your device."
read -p "Proceed (y/n)? " proceed

if [ "$proceed" = "Y" -o "$proceed" = "y" ]; then
	echo "- Installing HIAS MQTT BLE Agent service"
	sudo touch /lib/systemd/system/HIAS-MQTT-BLE-Agent.service
	echo "[Unit]" | sudo tee -a /lib/systemd/system/HIAS-MQTT-BLE-Agent.service
	echo "Description=HIAS MQTT BLE Agent service" | sudo tee -a /lib/systemd/system/HIAS-MQTT-BLE-Agent.service
	echo "After=multi-user.target" | sudo tee -a /lib/systemd/system/HIAS-MQTT-BLE-Agent.service
	echo "" | sudo tee -a /lib/systemd/system/HIAS-MQTT-BLE-Agent.service
	echo "[Service]" | sudo tee -a /lib/systemd/system/HIAS-MQTT-BLE-Agent.service
	echo "User=$USER" | sudo tee -a /lib/systemd/system/HIAS-MQTT-BLE-Agent.service
	echo "Type=simple" | sudo tee -a /lib/systemd/system/HIAS-MQTT-BLE-Agent.service
	echo "Restart=on-failure" | sudo tee -a /lib/systemd/system/HIAS-MQTT-BLE-Agent.service
	echo "ExecStart=/usr/bin/python3 /home/$USER/HIAS-MQTT-BLE-Agent/agent.py" | sudo tee -a /lib/systemd/system/HIAS-MQTT-BLE-Agent.service
	echo "" | sudo tee -a /lib/systemd/system/HIAS-MQTT-BLE-Agent.service
	echo "[Install]" | sudo tee -a /lib/systemd/system/HIAS-MQTT-BLE-Agent.service
	echo "WantedBy=multi-user.target" | sudo tee -a /lib/systemd/system/HIAS-MQTT-BLE-Agent.service
	echo "" | sudo tee -a /lib/systemd/system/HIAS-MQTT-BLE-Agent.service

	sudo systemctl enable HIAS-MQTT-BLE-Agent.service
	sudo systemctl start HIAS-MQTT-BLE-Agent.service

	echo "- Installed HIAS MQTT BLE Agent service!";
	exit 0
else
	echo $FMSG;
	exit 1
fi