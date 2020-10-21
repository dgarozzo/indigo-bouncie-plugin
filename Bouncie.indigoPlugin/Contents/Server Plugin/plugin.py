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

import os
import sys
import random

import time
import datetime

import json
import re
import requests


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
				self.logger.debug("HTTPd 2 plugin not enabled")
				return False
		else:
			self.logger.debug("HTTPd 2 plugin not found")
			return False
		
		return True
	


	########################################
	def startup(self):
		self.logger.debug(u"startup called")

		self.pollingInterval = int(self.pluginPrefs.get("pollingIntervalVehicleData", 60) )

		self.use_webhooks = bool(self.pluginPrefs.get("useWebhooks", False))
		if self.use_webhooks:
 
			if( httpdPluginIsEnabled() ):
				# set up for webhooks with the HTTPd 2 plugin
				indigo.server.subscribeToBroadcast("com.flyingdiver.indigoplugin.httpd2","httpd_bouncie-webhook", "webhook_handler")
		
			else: 		
				self.logger.error("HTTPd 2 plugin not enabled, disabling webhooks")
				self.use_webhooks = False        


	def shutdown(self):
		indigo.server.log(u"shutdown called")

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

						self.logger.debug(data)
						jsonResponse = json.loads(data)
						self.logger.debug( jsonResponse )
						
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
												'lon': -75.1234567, 
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
   												'lat': 40.0439193, 
   												'lon': -75.6634761, 
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
									if( 'long' in location ):
										keyValueList.append( {'key':'stats-location-long', 'value':location['long'] } )
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
						self.logger.debug( keyValueList )
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
            
			
			self.pollingInterval = int(valuesDict["pollingIntervalVehicleData"])

			self.use_webhooks = bool(valuesDict["useWebhooks"])
			
			if( self.use_webhooks ):

				if( self.httpdPluginIsEnabled() ):
				
					# ?? do we need to check to see if we are already subscribed? potential to subscribe multiple times?
					
					# set up for webhooks with the HTTPd 2 plugin
					indigo.server.subscribeToBroadcast("com.flyingdiver.indigoplugin.httpd2","httpd_bouncie-webhook", "webhook_handler")
		
				else: 		
					self.logger.debug("HTTPd 2 plugin not enabled, disabling webhooks")
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

				
		eventType = payload[ "eventType" ]
		
		# do we need to do any special handling based on event?
		
		'''
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
		elif eventType == "tripData":
			self.logger.debug( "tripData" )
		elif eventType == "tripMetrics":
			self.logger.debug( "tripMetrics" )
		elif eventType == "tripEnd":
			self.logger.debug( "tripEnd" )
		else:
			self.logger.debug("{}: Unknown eventType '{}', {}".format(dev.name, eventType, payload))
		'''
		
		# update the device with specifics on the event data received		
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



	# not used yet...	
	def _getTrips( self, imei ):
		self.logger.debug(u"_requestVehicle")

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
				self.logger.debug("Bearer %s" % jsonResponse["access_token"])
	
				headersData = {"Content-type": "application/x-www-form-urlencoded", "Authorization": "%s" % jsonResponse["access_token"]}

				r = requests.get(self.bouncieAPIBaseUrl + target, params=paramsList, timeout=2, headers=headersData)
				self.logger.debug( r )
			
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
			indigo.server.log("FYI - Exception caught _requestData: " + str(e))

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
	
		self.logger.debug(u"_requestVehicle")

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
			indigo.server.log("FYI - Exception caught _requestAccessToken: " + str(e))

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
			indigo.server.log("FYI - Exception caught saving access token: " + str(e))
			return False


	def renewAccessToken( self ):
	
		self.logger.debug(u"renewAccessToken")
		
		data = self._requestAccessToken(self.pluginPrefs["code"], self.pluginPrefs["clientId"], self.pluginPrefs["clientSecret"])

		if( not self._saveAccessToken(data) ):
			indigo.server.log( "Unable to automatically renew access token. Please re-configure Bouncie to renew access token." )
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

