#!/usr/bin/env python
""" HIAS iotJumpWay Agent Abstract Class

HIAS IoT Agents process all data coming from entities connected to the HIAS
iotJumpWay brokers.

MIT License

Copyright (c) 2021 Asociación de Investigacion en Inteligencia Artificial
Para la Leucemia Peter Moss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files(the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and / or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Contributors:
- Adam Milton-Barker

"""

import json
import psutil
import requests
import ssl
import threading

from abc import ABC, abstractmethod

from modules.helpers import Helpers
from modules.hiasbch import HIASBCH
from modules.hiascdi import HIASCDI
from modules.hiashdi import HIASHDI
from modules.mqtt import MQTT


class AbstractAgent(ABC):
	""" Abstract class representing a HIAS iotJumpWay IoT Agent.

	This object represents a HIAS iotJumpWay IoT Agent. HIAS IoT Agents
	process all data coming from entities connected to the HIAS iotJumpWay
	broker using the various machine to machine protocols.
	"""

	def __init__(self):
		"Initializes the AbstractAgent object."

		self.hiascdi = None
		self.hiashdi = None
		self.mqtt = None

		self.app_types = ["Robotics", "Application", "Staff"]

		self.helpers = Helpers("Agent")
		self.confs = self.helpers.confs
		self.credentials = self.helpers.credentials

		self.bles = []
		self.ble_tracker = {}

		self.helpers.logger.info(
			"Agent initialization complete.")

	def hiasbch_connection(self):
		"""Initializes the HIASBCH connection. """

		self.hiasbch = HIASBCH(self.helpers)
		self.hiasbch.start()
		self.hiasbch.w3.geth.personal.unlockAccount(
			self.hiasbch.w3.toChecksumAddress(self.credentials["hiasbch"]["un"]),
			self.credentials["hiasbch"]["up"], 0)

		self.helpers.logger.info(
			"HIAS HIASBCH Blockchain connection created.")

	def hiascdi_connection(self):
		"""Instantiates the HIASCDI Contextual Data Interface connection. """

		self.hiascdi = HIASCDI(self.helpers)

		self.helpers.logger.info(
			"HIASCDI Contextual Data Interface connection instantiated.")

	def hiashdi_connection(self):
		"""Instantiates the HIASCDI Historical Data Interface connection. """

		self.hiashdi = HIASHDI(self.helpers)

		self.helpers.logger.info(
			"HIASHDI Historical Data Interface connection instantiated.")

	def mqtt_connection(self, credentials):
		"""Initializes the HIAS MongoDB Database connection and subscribes
		to HIAS iotJumpWay topics. """

		self.mqtt = MQTT(self.helpers, "Agent", credentials)
		self.mqtt.configure()
		self.mqtt.start()

		self.helpers.logger.info(
			"HIAS iotJumpWay MQTT Broker connection created.")

	def get_attributes(self, entity_type, entity):
		"""Gets entity attributes from HIASCDI.

		Args:
			entity_type (str): The HIASCDI Entity type.
			entity (str): The entity id.

		Returns:
			dict: Required entity attributes

		"""

		attrs = self.hiascdi.get_attributes(entity_type, entity)

		rattrs = {}

		if entity_type in self.app_types:
			rattrs["id"] = attrs["id"]
			rattrs["type"] = attrs["type"]
			rattrs["blockchain"] = attrs["authenticationBlockchainUser"]["value"]
			rattrs["location"] = attrs["networkLocation"]["value"]
		else:
			rattrs["id"] = attrs["id"]
			rattrs["type"] = attrs["type"]
			rattrs["blockchain"] = attrs["authenticationBlockchainUser"]["value"]
			rattrs["location"] = attrs["networkLocation"]["value"]
			rattrs["zone"] = attrs["networkZone"]["value"]

		return rattrs

	def life(self):
		""" Publishes entity statistics to HIAS. """

		cpu = psutil.cpu_percent()
		mem = psutil.virtual_memory()[2]
		hdd = psutil.disk_usage('/').percent
		tmp = psutil.sensors_temperatures()['cpu_thermal'][0].current
		r = requests.get('http://ipinfo.io/json?token=' +
					self.credentials["iotJumpWay"]["ipinfo"])
		data = r.json()
		location = data["loc"].split(',')

		self.mqtt.publish("Life", {
			"CPU": float(cpu),
			"Memory": float(mem),
			"Diskspace": float(hdd),
			"Temperature": float(tmp),
			"Latitude": float(location[0]),
			"Longitude": float(location[1])
		})

		self.helpers.logger.info("Agent life statistics published.")
		threading.Timer(300.0, self.life).start()

	def threading(self):
		""" Creates required module threads. """

		# Life thread
		threading.Timer(10.0, self.life).start()
