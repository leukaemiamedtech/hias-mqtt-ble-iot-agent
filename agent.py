#!/usr/bin/env python3
""" HIAS Bluetooth IoT Agent Class

HIAS Bluetooth IoT Agents are bridges between HIAS devices that support
Bluetooth/Bluetooth Low Energy protocol and the HIASCDI Context Broker.

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

from gevent import monkey
monkey.patch_all()

import json
import os
import psutil
import signal
import sys
import time
import threading

from abc import ABC, abstractmethod
from bluepy import btle
from datetime import datetime, timedelta
from flask import Flask, request, Response
from threading import Thread

from modules.AbstractAgent import AbstractAgent

class Agent(AbstractAgent):
	""" HIAS Bluetooth IoT Agent Class

	HIAS Bluetooth IoT Agents are bridges between HIAS
	devices that support Bluetooth/Bluetooth Low Energy
	protocol and the HIASCDI Context Broker.
	"""

	def get_ble_devices(self):
		""" Returns a list of HIAS BLE devices """

		bles = self.hiascdi.get_ble_devices()

		for ble in bles:
			self.bles.append((
						ble["bluetoothAddress"]["value"],
						ble["bluetoothServiceUUID"]["value"],
						ble["bluetoothCharacteristicUUID"]["value"],
						ble["networkLocation"]["value"],
						ble["networkZone"]["value"],
						ble["id"]))

	def check_ble_devices(self):
		""" Checks for disconnected HIAS BLE devices """

		for device in self.ble_tracker:
			if self.ble_tracker[device]["last_seen"] != "" and self.ble_tracker[device]["last_seen"] < datetime.now() - timedelta(minutes=5):

				self.mqtt.device_status_publish(self.ble_tracker[device]["location"],
												self.ble_tracker[device]["zone"],
												self.ble_tracker[device]["device"],
												"OFFLINE")

				self.ble_tracker[device]["last_seen"] = ""

				self.helpers.logger.info(
					"BLE device " + self.ble_tracker[device]["address"] + " disconnected from iotJumpWay")

		threading.Timer(100.0, self.check_ble_devices).start()

	def ble_connection(self, addr, service, characteristic):
		""" Connects to a HIAS BLE device """

		while True:
			try:
				self.helpers.logger.info(
					"Attempting BLE connection to "+addr)

				peripheral = btle.Peripheral(addr)
				peripheral.setMTU(512)

				delegate = BtAgentDelegate()
				peripheral.withDelegate(delegate)

				serv = peripheral.getServiceByUUID(service)
				charac = serv.getCharacteristics(characteristic)[0]

				peripheral.writeCharacteristic(charac.valHandle + 1, b"\x01\x00")

				self.helpers.logger.info(
					"BLE connection to " + addr + " established")

				if addr in self.ble_tracker:
					self.ble_tracker[addr]["last_seen"] = datetime.now()
					self.helpers.logger.info(
						addr + " connection timestamp updated")


				self.notification_loop(peripheral)
			except Exception as e:
				self.helpers.logger.info(
					"BLE connection to " + addr + " failed")
				time.sleep(1.0)
				continue

	def notification_loop(self, peripheral):
		""" Notification loop """

		try:
			if peripheral.waitForNotifications(2.0):
				self.helpers.logger.info(
					"Awaiting notifications...")
		except Exception as e:
			pass
		finally:
			self.helpers.logger.info(
				"Disconnecting from HIAS BLE device")
			try:
				peripheral.disconnect()
				time.sleep(4)
			except Exception as e:
				self.helpers.logger.info(
					"Failed to disconnect from HIAS BLE device")
				pass

	def parse_data(self, data):
		""" Parses the data dictionary """

		entity_type = data["EntityType"]
		entity = data["Entity"]
		data_type = data["Type"]
		data_value = data["Value"]
		data_message = data["Message"]

		return entity_type, entity, data_type, data_value, data_message

	def respond(self, response_code, response):
		""" Returns the request repsonse """

		return Response(response=json.dumps(response, indent=4),
						status=response_code,
						mimetype="application/json")

	def signal_handler(self, signal, frame):
		self.helpers.logger.info("Disconnecting")
		self.mqtt.disconnect()
		sys.exit(1)

app = Flask(__name__)
agent = Agent()

class BtAgentDelegate(btle.DefaultDelegate):

	def __init__(self):
		btle.DefaultDelegate.__init__(self)

	def handleNotification(self, cHandle, data):

		data = json.loads(data.decode("utf-8"))

		if "EntityType" not in data:
			return
		if "Entity" not in data:
			return

		(entity_type, entity, data_type,
			data_value, data_message) = agent.parse_data(data)

		agent.helpers.logger.info(
			"Received " + entity_type + " data via BLE: " + str(data))

		attrs = agent.get_attributes(entity_type, entity)
		bch = attrs["blockchain"]

		if not agent.hiasbch.iotjumpway_check(bch):
			return

		_id = attrs["id"]

		location = attrs["location"]
		zone = attrs["zone"] if "zone" in attrs else "NA"
		sensor = data["Sensor"] if "Sensor" in data else "NA"
		actuator = data["Actuator"] if "Actuator" in data else "NA"

		if sensor != "NA":
			agent.helpers.logger.info("Processing sensors")

			sensors = agent.hiascdi.get_sensors(
				entity, entity_type)
			sensorData = sensors["sensors"]

			i = 0
			for sensor in sensorData["value"]:
				for prop in sensor["properties"]["value"]:
					if data["Type"].lower() in prop:
						sensorData["value"][i]["properties"]["value"][data["Type"].lower()] = {
							"value": data["Value"],
							"timestamp":  {
								"value": datetime.now().isoformat()
							}
						}
				i = i + 1

			updateResponse = agent.hiascdi.update_entity(
				entity, entity_type, {
					"networkStatus": {"value": "ONLINE"},
					"networkStatus.metadata": {"timestamp":  {
						"value": datetime.now().isoformat()
					}},
					"dateModified": {"value": datetime.now().isoformat()},
					"sensors": sensorData
				})

			if updateResponse:
				_id = agent.hiashdi.insert_data("Sensors", {
					"Use": entity_type,
					"Location": location,
					"Zone": zone,
					"Device": entity if entity_type == "Device" else "NA",
					"HIASCDI": entity if entity_type == "HIASCDI" else "NA",
					"Agent": entity if entity_type == "Agent" else "NA",
					"Application": entity if entity_type == "Application" else "NA",
					"Device": entity if entity_type == "Device" else "NA",
					"Staff": entity if entity_type == "Staff" else "NA",
					"Sensor": data["Sensor"],
					"Type": data["Type"],
					"Value": data["Value"],
					"Message": data["Message"],
					"Time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
				})

				if _id != False:
					agent.helpers.logger.info(
						entity_type + " " + entity + " sensors update OK")

					agent.mqtt.publish("Integrity", {
						"_id": str(_id),
						"Sensor": data["Sensor"],
						"Type": data["Type"],
						"Value": data["Value"],
						"Message": data["Message"]
					})

				else:
					agent.helpers.logger.error(
						entity_type + " " + entity + " sensors update KO")
			else:
				agent.helpers.logger.error(
					entity_type + " " + entity + " sensors update KO")

@app.route('/About', methods=['GET'])
def about():
	"""
	Returns Agent details
	Responds to GET requests sent to the North Port About API endpoint.
	"""

	return agent.respond(200, {
		"Identifier": agent.credentials["iotJumpWay"]["entity"],
		"Host": agent.credentials["server"]["ip"],
		"NorthPort": agent.credentials["server"]["port"],
		"CPU": psutil.cpu_percent(),
		"Memory": psutil.virtual_memory()[2],
		"Diskspace": psutil.disk_usage('/').percent,
		"Temperature": psutil.sensors_temperatures()['coretemp'][0].current
	})

def main():

	signal.signal(signal.SIGINT, agent.signal_handler)
	signal.signal(signal.SIGTERM, agent.signal_handler)

	agent.hiascdi_connection()
	agent.get_ble_devices()
	agent.hiashdi_connection()
	agent.hiasbch_connection()

	agent.mqtt_connection({
		"host": agent.credentials["iotJumpWay"]["host"],
		"port": agent.credentials["iotJumpWay"]["port"],
		"location": agent.credentials["iotJumpWay"]["location"],
		"zone": agent.credentials["iotJumpWay"]["zone"],
		"entity": agent.credentials["iotJumpWay"]["entity"],
		"name": agent.credentials["iotJumpWay"]["name"],
		"un": agent.credentials["iotJumpWay"]["un"],
		"up": agent.credentials["iotJumpWay"]["up"]
	})

	for ble in agent.bles:
		agent.ble_tracker[ble[0]] = {
			"location": ble[3],
			"zone": ble[4],
			"device": ble[5],
			"address": ble[0],
			"last_seen": ""
		}
		Thread(target=agent.ble_connection, args=(ble[0], ble[1], ble[2]), daemon=True).start()

	Thread(target=agent.life, args=(), daemon=True).start()
	Thread(target=agent.check_ble_devices, args=(), daemon=True).start()

	app.run(host=agent.helpers.credentials["server"]["ip"],
			port=agent.helpers.credentials["server"]["port"])

if __name__ == "__main__":
	main()
