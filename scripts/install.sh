#!/bin/bash

PRN="HIAS Bluetooth IoT Agent"
FMSG="- $PRN installation terminated"

read -p "? This script will install the $PRN on your device. Are you ready (y/n)? " cmsg

if [ "$cmsg" = "Y" -o "$cmsg" = "y" ]; then
	echo "- Installing $PRN"
	pip3 install --user flask
	pip3 install --user gevent
	pip3 install --user psutil
	pip3 install --user requests
	pip3 install --user web3
	pip3 install --user gevent
	echo "- $PRN installed!"
else
	echo $FMSG;
	exit
fi