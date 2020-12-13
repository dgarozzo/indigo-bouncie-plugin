#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

# http://joyunspeakable.com
# david@joyunspeakable.com

# MIT License

# Copyright (c) 2020 David Garozzo

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import indigo

import logging

import os
import sys
import random

import time
import datetime

import json
import re
import requests

import httplib, urllib


# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

################################################################################
class Plugin(indigo.PluginBase):


	bouncieAPIBaseUrl = "https://api.bouncie.dev/v1/"



	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

		self.logger = logging.getLogger("Plugin.Bouncie")
		
		self.triggerDict = {}

		try:
			self.logLevel = int(self.pluginPrefs[u"logLevel"])
		except:
			self.logLevel = logging.INFO
		self.indigo_log_handler.setLevel(self.logLevel)
		self.logger.debug(u"logLevel = {}".format(self.logLevel))


	def httpdPluginIsEnabled(self):

		httpd_plugin = indigo.server.getPlugin("com.flyingdiver.indigoplugin.httpd2")
		if( httpd_plugin ):
			if not httpd_plugin.isEnabled():
				self.logger.error("HTTPd 2 plugin not enabled")
				return False
		else:
			self.logger.warning("HTTPd 2 plugin not found")
			return False
		
		return True
	


	########################################
	def startup(self):
		self.logger.debug(u"startup called")

		self.pollingInterval = int(self.pluginPrefs.get("pollingIntervalVehicleData", 60) )

		self.use_webhooks = bool(self.pluginPrefs.get("useWebhooks", False))
		if not self.use_webhooks:
			self.logger.warning("webhooks disabled")
			return
 
 		if( self.httpdPluginIsEnabled() ):
			# set up for webhooks with the HTTPd 2 plugin
			self.logger.debug("setting up webhooks")
			indigo.server.subscribeToBroadcast("com.flyingdiver.indigoplugin.httpd2","httpd_bouncie-webhook", "webhook_handler")
 		
 		else: 		
			self.logger.error("HTTPd 2 plugin not enabled, disabling webhooks")
			self.use_webhooks = False        


	def shutdown(self):
		self.logger.debug(u"shutdown called")

	########################################
	def runConcurrentThread(self):
		try:
			while True:
				for dev in indigo.devices.iter("self"):
					if not dev.enabled or not dev.configured:
						continue

					# Plugins that need to poll out the status from the sensor
					# could do so here, then broadcast back the new values to the
					# Indigo Server via updateStateOnServer. For this example, we
					# could toggle the onOffState every 2 seconds. If the sensor
					# always broadcasts out changes (or is just 1-way), then this
					# entire runConcurrentThread() method can be deleted.
					if dev.deviceTypeId == u"myBouncieCustomType":
					
						imei = dev.pluginProps.get("vehicle", "")
						if( imei == "" ):
							self.logger.error(u"problem with device configuration. unable to get imei. please reconfigue.")
							continue
							
						data = self._requestVehicle( imei )
						
						if( data == "" ):
							self.logger.error( u"problem getting vehicle data for imei: %s" % imei )
							continue

						#self.logger.debug(data)
						jsonResponse = json.loads(data)
						#self.logger.debug( jsonResponse )
						
						'''
						# sample response from vehicles:
						[
							{
								'stats': 
									{
										'isRunning': False, 
										'mil': 
											{
												'milOn': False, 
												'lastUpdated': '2020-10-15T22:19:58.000Z'
											}, 
										'lastUpdated': '2020-10-17T18:51:50.000Z', 
										'location': 
											{
												'lat': 40.1234567, 
												'lon': -75.123456, 
												'heading': 312, 
												'address': None
											}, 
										'localTimeZone': '-0400', 
										'speed': 1.242742
									}, 
								'vin': '12345123451234512', 
								'standardEngine': '3L', 
								'imei': '111112222233333', 
								'model': 
									{
										'make': 'AUDI', 
										'name': 'S4', 
										'year': 2013
									}, 
								'nickName': 'Audi S4'
							}
						]						


   						[
   							{
   								'imei': '444445555566666', 
   								'stats': 
   									{
   										'isRunning': False, 
   										'fuelLevel': 37.26436845296366, 
   										'battery': 
   											{
   												'status': 'normal', 
   												'lastUpdated': '2020-10-17T22:29:22.000Z'
   											},
   										'lastUpdated': '2020-10-17T19:34:17.000Z', 
   										'location': 
   											{
   												'lat': 40.1234567, 
   												'lon': -75.123456, 
   												'heading': 149, 
   												'address': None
   											}, 
   										'localTimeZone': '-0400', 
   										'speed': 0
   									}, 
   								'model': 
   									{
   										'make': 'HONDA', 
   										'name': 'Odyssey',
   										'year': 2018
   									},
   								'vin': '67896789678967896', 
   								'standardEngine': '3.5L V6'
   							}
   						]
						'''

						keyValueList = []
						keyValueList.append( {'key':'vehicleJSON', 'value':data } )

						for result in jsonResponse:
							if( 'model' in result ):
								model = result['model']
								if( 'make' in model ):
									keyValueList.append( {'key':'model-make', 'value':model['make'] } )
								if( 'name' in model ):
									keyValueList.append( {'key':'model-name', 'value':model['name'] } )
								if( 'year' in model ):
									keyValueList.append( {'key':'model-year', 'value':model['year'] } )
							if( 'nickname' in result ):
								keyValueList.append( {'key':'nickname', 'value':result['nickname'] } )
							if( 'standardEngine' in result ):
								keyValueList.append( {'key':'standardEngine', 'value':result['standardEngine'] } )
							if( 'vin' in result ):
								keyValueList.append( {'key':'vin', 'value':result['vin'] } )
							if( 'imei' in result ):
								keyValueList.append( {'key':'imei', 'value':result['imei'] } )
							if( 'stats' in result ):
								stats = result['stats']
								if( 'localTimezone' in stats ):
									keyValueList.append( {'key':'stats-localTimezone', 'value':stats['localTimezone'] } )
								if( 'lastUpdated' in stats ):
									keyValueList.append( {'key':'stats-lastUpdated', 'value':stats['lastUpdated'] } )
								if( 'location' in stats ):
									location = stats['location']
									if( 'lat' in location ):
										keyValueList.append( {'key':'stats-location-lat', 'value':location['lat'] } )
									if( 'lon' in location ):
										keyValueList.append( {'key':'stats-location-long', 'value':location['lon'] } )
									if( 'heading' in location ):
										keyValueList.append( {'key':'stats-location-heading', 'value':location['heading'] } )
									if( 'address' in location ):
										keyValueList.append( {'key':'stats-location-address', 'value':location['address'] } )
								if( 'fuelLevel' in stats ):
									keyValueList.append( {'key':'stats-fuelLevel', 'value':stats['fuelLevel'] } )
								if( 'isRunning' in stats ):
									keyValueList.append( {'key':'stats-isRunning', 'value':stats['isRunning'] } )
								if( 'speed' in stats ):
									keyValueList.append( {'key':'stats-speed', 'value':stats['speed'] } )
								if( 'mil' in stats ):
									mil = stats['mil']
									if( 'milOn' in mil ):
										keyValueList.append( {'key':'mil-milOn', 'value':mil['milOn'] } )
									if( 'lastUpdated' in mil ):
										keyValueList.append( {'key':'mil-lastUpdated', 'value':mil['lastUpdated'] } )
								if( 'battery' in stats ):
									battery = stats['battery']
									if( 'status' in battery ):
										keyValueList.append( {'key':'battery-status', 'value':battery['status'] } )
									if( 'lastUpdated' in battery ):
										keyValueList.append( {'key':'battery-lastUpdated', 'value':battery['lastUpdated'] } )
						#self.logger.debug( keyValueList )
						dev.updateStatesOnServer( keyValueList )

						'''
						data = self._getTrips( imei )
						
						if( data == "" ):
							self.logger.debug( u"problem getting vehicle trips for imei: %s" % imei )
							continue

						#self.logger.debug(data)
						jsonResponse = json.loads(data)
						self.logger.debug( jsonResponse )
						'''

				self.sleep(self.pollingInterval)
		except self.StopThread:
			pass	# Optionally catch the StopThread exception and do any needed cleanup.

	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		return (True, valuesDict)


	########################################
	def validatePrefsConfigUi(self, valuesDict):
		errorsDict = indigo.Dict()
		try:
			if int(valuesDict['pollingIntervalVehicleData']) < 5:
				raise Exception()
		except:
			errorsDict["pollingIntervalVehicleData"] = u"Must be a number greater than or equal to 5 (seconds)."
		if len(errorsDict):
			return False, valuesDict, errorsDict
		return True, valuesDict


	########################################
	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		if( not userCancelled ):
		
			try:
				self.logLevel = int(valuesDict[u"logLevel"])
			except:
				self.logLevel = logging.INFO
			self.indigo_log_handler.setLevel(self.logLevel)
			self.logger.debug(u"logLevel = {}".format(self.logLevel))

			#self.debug = valuesDict["debugLogging"]

			self.pollingInterval = int(valuesDict["pollingIntervalVehicleData"])

			self.use_webhooks = bool(valuesDict["useWebhooks"])
			
			if( self.use_webhooks ):

				if( self.httpdPluginIsEnabled() ):
				
					# ?? do we need to check to see if we are already subscribed?
					
					# set up for webhooks with the HTTPd 2 plugin
					indigo.server.subscribeToBroadcast("com.flyingdiver.indigoplugin.httpd2","httpd_bouncie-webhook", "webhook_handler")
		
				else: 		
					self.logger.error("HTTPd 2 plugin not enabled, disabling webhooks")
					self.use_webhooks = False        
			
		return (True)
		

	########################################
	def deviceStartComm(self, dev):
		# Called when communication with the hardware should be started.
		self.logger.debug("deviceStartComm")

		# subModel is set in UI so it is inside pluginProps, but we want to push the value
		# down into the actual dev.subModel attribute:
		subModel = dev.pluginProps.get("subModel", "")
		if dev.subModel != subModel:
			dev.subModel = subModel
			dev.replaceOnServer()


	def deviceStopComm(self, dev):
		# Called when communication with the hardware should be shutdown.
		pass




	def webhook_handler(self, hookJson ):
    
		# HTTPd 2 Debug                   MyRequestHandler: POST to port 5555 from 192.168.1.251:57404 for /bouncie-webhook
		# HTTPd 2 Debug                   MyRequestHandler: No password specified in device configuration, skipping authentication
		# HTTPd 2 Debug                   do_webhook query = , path = /bouncie-webhook
		# HTTPd 2 Debug                   Webhook to httpd_bouncie-webhook = 
		# {
		#	"headers": 
		#		{	
		#			"origin": "http://192.168.1.240:5555", 
		#			"content-length": "258", 
		#			"accept-language": "en-US,en;q=0.5", 
		#			"accept-encoding": "gzip, deflate", 
		#			"connection": "keep-alive", 
		#			"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", 
		#			"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:81.0) Gecko/20100101 Firefox/81.0", 
		#			"host": "192.168.1.240:5555", 
		#			"cookie": "plushContainerWidth=100%25; plushMultiOps=1; plushNoTopMenu=0", 
		#			"pragma": "no-cache", 
		#			"cache-control": "max-age=0, no-cache", 
		#			"upgrade-insecure-requests": "1"
		#		}, 
		#	"request": 
		#		{
		#			"path": "/bouncie-webhook", 
		#			"client": "192.168.1.251", 
		#			"command": "POST"
		#		}, 
		#	"payload": "{\n    \"eventType\": \"connect\",\n    \"imei\": \"111112222233333\",\n    \"vin\": \"12345123451234512\",\n    \"connect\": {\n        \"timestamp\": \"2019-07-01T15:04:57.000Z\",\n        \"timeZone\": \"-0500\",\n        \"latitude\": 32.111111,\n        \"longitude\": -96.111111\n    }\n}", 
		#	"vars": {}
		# }
		
		hookData = json.loads(hookJson)

		self.logger.debug(u"webhook_handler received: %s" % hookData )
		
		
		# pull the imei out of the payload
		payload = json.loads( hookData[ "payload" ] )

		# Find the Indigo device for the Bouncie Device
		for dev in indigo.devices.iter(filter="self"):
			if dev.pluginProps.get("vehicle", "") == payload['imei']:
				break
		else:
			self.logger.debug("webHook_handler: No matching Indigo device for Bouncie imei '{}'".format(payload['imei']))
			return

		# update that device with specifics on the event data received
				
		eventType = payload[ "eventType" ]
		
		if eventType == "connect":
			self.logger.debug( "connect" )
		elif eventType == "disconnect":
			self.logger.debug( "disconnect" )
		elif eventType == "battery":
			self.logger.debug( "battery" )
		elif eventType == "mil":
			self.logger.debug( "mil" )
		elif eventType == "tripStart":
			self.logger.debug( "tripStart" )
			dev.updateStateOnServer( "previousMilesFromHome", 0.0 )
			dev.updateStateOnServer( "currentMilesFromHome", 0.0 )
		elif eventType == "tripData":
			self.logger.debug( "tripData" )
		elif eventType == "tripMetrics":
			self.logger.debug( "tripMetrics" )
		elif eventType == "tripEnd":
			self.logger.debug( "tripEnd" )
			dev.updateStateOnServer( "previousMilesFromHome", 0.0 )
			dev.updateStateOnServer( "currentMilesFromHome", 0.0 )
		else:
			self.logger.debug("{}: Unknown eventType '{}', {}".format(dev.name, eventType, payload))

		dev.updateStateOnServer( "webHookJSON-%s" % eventType, hookData[ "payload" ] )

		# fire off the event
		self._fireTrigger(eventType, payload['imei'])
			
		return
		


	######################################################################################
	# Indigo Trigger Start/Stop
	######################################################################################

	########################################
	def triggerStartProcessing(self, trigger):
		super(Plugin, self).triggerStartProcessing(trigger)
		self.logger.debug("Start processing trigger " + str(trigger.id))
		if trigger.id not in self.triggerDict:
			self.triggerDict[trigger.id] = trigger
		self.logger.debug("Start trigger processing list: " + str(self.triggerDict))

	########################################
	def triggerStopProcessing(self, trigger):
		super(Plugin, self).triggerStopProcessing(trigger)
		self.logger.debug("Stop processing trigger " + str(trigger.id))
		try:
			del self.triggerDict[trigger.id]
		except:
			# the trigger isn't in the list for some reason so just skip it
			pass
		self.logger.debug("Stop trigger processing list: " + str(self.triggerDict))


	######################################################################################
	# Indigo Trigger Firing
	######################################################################################	
			
	def _fireTrigger(self, event, imei=None):
		try:
			self.logger.debug( "_fireTrigger - event: %s, imei: %s" % ( event, imei ) )
			for triggerId, trigger in self.triggerDict.items():
				#self.logger.debug( trigger )
				if trigger.pluginTypeId == event:
					if trigger.pluginProps["vehicle"] == imei:
						indigo.trigger.execute(trigger)

		except Exception as exc:
			self.logger.error(u"An error occurred during trigger processing")







	########################################
	# Sensor Action callback
	######################
	'''
	def actionControlSensor(self, action, dev):
		###### TURN ON ######
		# Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
		if action.sensorAction == indigo.kSensorAction.TurnOn:
			indigo.server.log(u"ignored \"%s\" %s request (sensor is read-only)" % (dev.name, "on"))
			# But we could request a sensor state update if we wanted like this:
			# dev.updateStateOnServer("onOffState", True)

		###### TURN OFF ######
		# Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
		elif action.sensorAction == indigo.kSensorAction.TurnOff:
			indigo.server.log(u"ignored \"%s\" %s request (sensor is read-only)" % (dev.name, "off"))
			# But we could request a sensor state update if we wanted like this:
			# dev.updateStateOnServer("onOffState", False)

		###### TOGGLE ######
		# Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
		elif action.sensorAction == indigo.kSensorAction.Toggle:
			indigo.server.log(u"ignored \"%s\" %s request (sensor is read-only)" % (dev.name, "toggle"))
			# But we could request a sensor state update if we wanted like this:
			# dev.updateStateOnServer("onOffState", not dev.onState)
	'''
	
	########################################
	# General Action callback
	######################
	'''
	def actionControlUniversal(self, action, dev):
		###### BEEP ######
		if action.deviceAction == indigo.kUniversalAction.Beep:
			# Beep the hardware module (dev) here:
			# ** IMPLEMENT ME **
			indigo.server.log(u"sent \"%s\" %s" % (dev.name, "beep request"))

		###### STATUS REQUEST ######
		elif action.deviceAction == indigo.kUniversalAction.RequestStatus:
			# Query hardware module (dev) for its current status here:
			# ** IMPLEMENT ME **
			indigo.server.log(u"sent \"%s\" %s" % (dev.name, "status request"))
	'''
	
	########################################
	# Custom Plugin Action callbacks (defined in Actions.xml)
	######################

	def getLatLongData( self, dev ):

		'''
		# webhookJSON-tripData
		{
		  "eventType": "tripData",
		  "imei": "12345123451234512",
		  "vin": "111112222233333",
		  "transactionId": "352602110001168-219-1607722515000",
		  "data": [
			{
			  "timestamp": "2020-12-11T21:58:15.000Z",
			  "timezone": "-0500",
			  "speed": 0,
			  "gps": {
				"lat": 40.1111111,
				"lon": -75.1111111,
				"obdMaxSpeed": 58.408874,
				"obdAverageSpeed": 26.097582,
				"heading": 128,
				"satelliteCount": 13,
				"hdop": 1.5
			  }
			}
		  ]
		}
		'''
		retVal = dict()
		retVal[ "latLongCSV" ] = None
		retVal[ "latLongTimestamp" ] = None
		retVal[ "latLongTimezone" ] = None
		
		# first, check to see if we have webhookJSON-tripData data
		latLongCSV = None
		try:
	
			tripData = dev.states["webHookJSON-tripData"]
			#self.logger.debug( tripData )
			tripDataJson = json.loads( tripData )
			latLongCSV = "%s,%s" % ( tripDataJson[ "data" ][ 0 ][ "gps" ][ "lat" ], tripDataJson[ "data" ][ 0 ][ "gps" ][ "lon" ] )
			self.logger.debug( "webHookJSON-tripData: %s" % latLongCSV )
			latLongTimestamp = tripDataJson[ "data" ][ 0 ][ "timestamp" ]
			latLongTimeszone = tripDataJson[ "data" ][ 0 ][ "timezone" ]
				
		except:
	
			try:
				# if not, check stats-location-lat, stats-location-long
				statsLocationLat = dev.states["stats-location-lat"]
				statsLocationLong = dev.states["stats-location-long"]
			
				if( ( statsLocationLat == "" ) or ( statsLocationLong == "" ) ):
					return retVal

				latLongCSV = "%s,%s" % (statsLocationLat, statsLocationLong )
				self.logger.debug( "stats-location: %s" % latLongCSV )
				latLongTimestamp = dev.states["stats-lastUpdated"]
				latLongTimeszone = ""
			except:
				return retVal

		retVal[ "latLongCSV" ] = latLongCSV
		retVal[ "latLongTimestamp" ] = latLongTimestamp
		retVal[ "latLongTimezone" ] = latLongTimeszone
		
		return retVal

	"""
		Get ETA via Google Distance Matrix ****************************************************
	"""
	def getGoogleDistanceMatrix(self, dev, latLongCSV):

		try:
			self.logger.debug( "getGoogleDistanceMatrix for %s" % dev.name )
			
			googleMapsApiKey = self.pluginPrefs["googleMapsAPIKey"]
			
			##self.logger.debug( googleMapsApiKey )

			theUrl = 'https://maps.googleapis.com/maps/api/distancematrix/json?origins='+str(latLongCSV)+'&' + urllib.urlencode({'destinations':self.pluginPrefs["homeAddress"]}) + '&key='+googleMapsApiKey+'&units=imperial'
			self.logger.debug( theUrl )
			
			response = requests.get(theUrl, timeout=2)
			
			self.logger.debug( response.text )

			dev.updateStateOnServer( "googleapis-distancematrix", response.text )
			
			distanceMatrixJson = json.loads(response.text)
			
			# Record last ETA Distance and this ETA Distance to help determine if we'll notify en route
			distance = str(distanceMatrixJson['rows'][0]['elements'][0]['distance']['text']).split()
			
			#self.logger.debug( distance )
			
			if distance[1] == 'mi':
				dev.updateStateOnServer( 'currentMilesFromHome', float(distance[0]) )
			else:
				dev.updateStateOnServer( 'currentMilesFromHome', 0.0 )


			try:
				percentChange = ((dev.states['previousMilesFromHome'] - dev.states['currentMilesFromHome']) / dev.states['previousMilesFromHome']) * 100
			except Exception, e:
				# Divide by zero when car[vehicleId]['previousMilesFromHome'] is zero
				percentChange = 0.0
				dev.updateStateOnServer( 'previousMilesFromHome', dev.states['currentMilesFromHome'] )
			
			# Only notify en route if there is a significant change in progress towards the house (or we're less than a mile away)
			if percentChange > 50.0 or dev.states['currentMilesFromHome'] == 0.0:
				dev.updateStateOnServer( 'previousMilesFromHome', dev.states['currentMilesFromHome'] )
				if percentChange > 50.0:
					
					self._fireTrigger("approaching_home", dev.states['imei'])

				#indigo.server.log(dev.name + " En Route; At " + location + ", " + ETA)
			else:
				self.logger.debug("Skipping due to lack of progress *towards* home; percent change = " + str(percentChange)) 


			
			return distanceMatrixJson
		
		except Exception, e:
			self.logger.error('Location unknown, distance matrix calculation failed: ' + str(e))
			return None
		
		return None


	def getETA(self, pluginAction, dev):
		
		self.logger.debug( "getETA for \"%s\"" % (dev.name) )

		eta = "Unknown"
		
		latLongData = self.getLatLongData( dev )
		
		if( latLongData[ "latLongCSV" ] == None ):
			dev.updateStateOnServer( "ETA", eta )
			self.logger.debug( eta )
			return eta
		
		distanceMatrixJson = self.getGoogleDistanceMatrix( dev, latLongData[ "latLongCSV" ] )
		
		if( distanceMatrixJson != None ):
		
			'''
			{
			   "destination_addresses" : [ "West Chester, PA 19380, USA" ],
			   "origin_addresses" : [ "180 Eagleview Blvd, Exton, PA 19341, USA" ],
			   "rows" : [
				  {
					 "elements" : [
						{
						   "distance" : {
							  "text" : "6.7 mi",
							  "value" : 10738
						   },
						   "duration" : {
							  "text" : "18 mins",
							  "value" : 1071
						   },
						   "status" : "OK"
						}
					 ]
				  }
			   ],
			   "status" : "OK"
			}			
			'''
			text = distanceMatrixJson['rows'][0]['elements'][0]['duration']['text']
			seconds = distanceMatrixJson['rows'][0]['elements'][0]['duration']['value']
			
			# when did we get this geoLocation data?
			self.logger.debug( str(latLongData[ "latLongTimestamp" ]) )
			
			if '.' in str(latLongData[ "latLongTimestamp" ]):
				timestamp = datetime.datetime.strptime(str(latLongData[ "latLongTimestamp" ]), '%Y-%m-%dT%H:%M:%S.%fZ')
			else:
				timestamp = datetime.datetime.strptime(str(latLongData[ "latLongTimestamp" ]), '%Y-%m-%dT%H:%M:%SZ')
			
			if( str( latLongData[ "latLongTimezone" ] ) != "" ):
				offset = int( str( latLongData[ "latLongTimezone" ] )[ -4:-2 ] )
				if( str( latLongData[ "latLongTimezone" ] )[0] == "-" ):
					offset = -offset
				timestamp = timestamp + datetime.timedelta(hours=offset)
		
			# Give ETA as event timestamp plus google travel time to home
			ETA = timestamp + datetime.timedelta(seconds=seconds)
		
			#self.logger.debug( ETA )
			
			eta = text + " / " + str(dev.states['currentMilesFromHome']) + " miles from home, ETA " + ETA.strftime("%I:%M %p")
			self.logger.debug( eta )
			dev.updateStateOnServer( "ETA", eta )
			
			dev.updateStateOnServer( "formatted_address", str( distanceMatrixJson['origin_addresses'][ 0 ] ) )
			
		return eta
	
	
	
	"""
		Google Geocode Location ****************************************************
	"""
	def getGeocodeLocation(self, dev, latLongCSV):
		
		responseJson = None

		try:
			self.logger.debug("getLocation %s" % dev.name)

			googleMapsApiKey = self.pluginPrefs["googleMapsAPIKey"]
	
			#self.logger.debug( googleMapsApiKey )
			
			apiURL = 'https://maps.googleapis.com/maps/api/geocode/json?latlng='+str(latLongCSV)+'&key='+googleMapsApiKey
			##self.logger.debug( apiURL )
						
			response = requests.get(apiURL, timeout=2)

			##self.logger.debug( response.text )

			dev.updateStateOnServer( "googleapis-geocode", response.text )

			responseJson = json.loads(response.text)
			
			dev.updateStateOnServer( "formatted_address", str( responseJson['results'][0]['formatted_address'] ) )
			
			return responseJson

		except Exception, e:
			iself.logger.error('Location unknown, geocode failed: ' + str(e))
			pass
	
		return responseJson


	def getAddress(self, pluginAction, dev):
		
		self.logger.debug( "getAddress for \"%s\"" % (dev.name) )

		currentStreet = "Unknown"
		
		latLongData = self.getLatLongData( dev )
		
		if( latLongData[ "latLongCSV" ] == None ):
			dev.updateStateOnServer( "currentStreet", currentStreet )
			self.logger.debug( currentStreet )
			return currentStreet
		
		locationJson = self.getGeocodeLocation( dev, latLongData[ "latLongCSV" ] )
	
		if( locationJson != None ):
		
			for component in locationJson['results'][0]['address_components']:
				self.logger.debug( "for loop address_components" )
				if component['types'][0] == 'route':
					currentStreet = component['long_name']
					self.logger.debug( "route found %s" % currentStreet )
					break
		
			self.logger.debug( "getLocation: %s" % currentStreet )
			dev.updateStateOnServer( "currentStreet", currentStreet )
			return currentStreet

		self.logger.debug( currentStreet )
		return currentStreet

	

	def _getTrips( self, imei ):
		#self.logger.debug(u"_requestVehicle")

		# gps-format can be either 'geojson' or 'polyline'
		
		data = self._requestData("trips", { 'imei': imei, 'gps-format': 'geojson' } )
		return data
	

	############################
	# Devices.xml callback methods
	############################


	def _requestData(self, target, paramsList={}):
	
		retries = 3
		data = ""
		try:
		
			while retries > 0:
			
				jsonResponse = json.loads(self.pluginPrefs['accessTokenJson'])
				#self.logger.debug("Bearer %s" % jsonResponse["access_token"])
	
				headersData = {"Content-type": "application/x-www-form-urlencoded", "Authorization": "%s" % jsonResponse["access_token"]}

				r = requests.get(self.bouncieAPIBaseUrl + target, params=paramsList, timeout=2, headers=headersData)
				#self.logger.debug( r )
			
				if( r.status_code == 200 ):
					data = r.text
					retries = 0
					continue
					
				else:
					retries -= 1
					# problem getting data
					if( r.status_code == 401 ):
						
						# access token expired?
						self.renewAccessToken()
						

		except Exception, e:
			self.logger.error("FYI - Exception caught _requestData: " + str(e))

		return data


	'''
	https://api.bouncie.dev/v1/vehicles

	[
	  {
		"model": {
		  "make": "GMC",
		  "name": "Terrain",
		  "year": 2012
		  },
		"nickName":"My Gmc",
		"standardEngine": "2.4L",
		"vin": "111112222233333",
		"imei": "12345123451234512",
		"stats": {
		  "localTimezone": "-0600",
		  "lastUpdated": "2020-04-28 22:13:17.000Z",
		  "location": "123 Main St, Dallas, Texas 75251, United States",
		  "fuelLevel": 27.3,
		  "isRunning": false,
		  "speed": 0,
		  "mil": {
			"milOn": false,
			"lastUpdated": "2020-01-01 12:00:00:000Z"
		  },
		  "battery": {
			"status": "normal",
			"lastUpdated": "2020-04-25 12:00:00:000Z"
		  }
		}
	  }
	]
	'''

	def _requestVehicle( self, imei ):
	
		#self.logger.debug(u"_requestVehicle")

		data = self._requestData("vehicles", { 'imei': imei } )
		return data
		

	def _requestVehicles(self):
	
		self.logger.debug(u"_requestVehicles")

		data = self._requestData("vehicles")
		return data


	def _getVehicles(self):
	
		self.logger.debug(u"_getVehicles")
		
		data = self._requestVehicles()
		
		self.logger.debug(data)
		jsonResponse = json.loads(data)
		
		myArray = []
		for result in jsonResponse:
			if( ( 'nickName' in result ) and ( result['nickName'] != None ) ):
				self.logger.debug( result['nickName'] )
				myArray.append( [ result['imei'], result['nickName'] ] )
			else:
				self.logger.debug( "%s %s %s" % ( result['model']['make'], result['model']['name'], result['model']['year'] ) )
				myArray.append( [ result['imei'], "%s %s %s" % ( result['model']['make'], result['model']['name'], result['model']['year'] ) ] )

		return myArray
		

	def getVehiclesList(self, filter="", valuesDict=None, typeId="", targetId=0):
	
		self.logger.debug(u"getVehiclesList")

		myArray = []
		
		try:
			myArray = self._getVehicles()
		except Exception, e:
			indigo.server.log("FYI - Exception caught getting vehicles list: " + str(e))
			
		return myArray









	########################################
	# Plugin Config callbacks (defined in PluginConfig.xml)
	######################
	def getAuthorization(self, valuesDict):
		
		self.logger.debug(u"getAuthorization")
		
		authorizationURL = "https://auth.bouncie.com/dialog/authorize?client_id=%s&redirect_uri=http://localhost/&response_type=code&state=initBouncieAuth" % ( valuesDict[ "clientId" ] )
		
		self.logger.debug( authorizationURL )
		self.browserOpen( authorizationURL )
		
		return valuesDict







	def _requestAccessToken(self, code, clientId, clientSecret):
		data = ""
		try:
			postURL = "/oauth/token"

			headersData = {"Content-type": "application/x-www-form-urlencoded", "Accept": "*/*", "User-Agent": "BouncieIndigoPlugin"}
			postData = {'client_id': clientId, 'client_secret': clientSecret, 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': 'http://localhost/' }
			r = requests.post('https://auth.bouncie.com' + postURL, timeout=2, headers=headersData, data=postData)
			data = r.text

			self.logger.debug(data)
		except Exception, e:
			self.logger.error("FYI - Exception caught _requestAccessToken: " + str(e))

		return data
		
	def _saveAccessToken(self, data):

		try:
			jsonResponse = json.loads(data)
			
			# this will throw if access_token does not exist
			self.logger.debug(jsonResponse["access_token"])

			# store the access token!
			# or maybe store the whole response??
			self.pluginPrefs["accessTokenJson"] = data
			
			return True
		except Exception, e:
			self.logger.error("FYI - Exception caught saving access token: " + str(e))
			return False


	def renewAccessToken( self ):
	
		self.logger.debug(u"renewAccessToken")
		
		data = self._requestAccessToken(self.pluginPrefs["code"], self.pluginPrefs["clientId"], self.pluginPrefs["clientSecret"])

		if( not self._saveAccessToken(data) ):
			self.logger.error( "Unable to automatically renew access token. Please re-configure Bouncie to renew access token." )
			return False

		return True


	def getAccessToken(self, valuesDict):
		
		self.logger.debug(u"getAccessToken")
		
		valuesDict["accessTokenFailCheckbox"] = "false"
	
		# extract value of code from the CallbackURL
		m = re.search('code=([0-9a-zA-Z]*)', valuesDict["callbackURL"])

		if m:
			code = m.group(1)
			self.logger.debug(code)
		else:
			self.logger.debug( 'invalud URL format - code not found' )
			valuesDict["callbackURL"] = ""
			valuesDict["accessTokenFailCheckbox"] = "true"
			return valuesDict
		
		data = self._requestAccessToken(code, valuesDict["clientId"], valuesDict["clientSecret"])

		if self._saveAccessToken(data):

			try:
				self.pluginPrefs["code"] = code
				self.pluginPrefs["clientId"] = valuesDict["clientId"]
				self.pluginPrefs["clientSecret"] = valuesDict["clientSecret"]

				valuesDict["accessTokenFailCheckbox"] = "success"
				valuesDict["accessTokenJson"] = data

			except Exception, e:
				indigo.server.log("FYI - Exception caught saving clientId and Secret: " + str(e))			
			
		else:
			indigo.server.log( 'unable to save access_token' )
			valuesDict["callbackURL"] = ""
			valuesDict["accessTokenJson"] = ""
			valuesDict["accessTokenFailCheckbox"] = "true"
		
		return valuesDict

