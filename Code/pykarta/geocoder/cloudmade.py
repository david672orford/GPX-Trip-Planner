#! /usr/bin/python
# pykarta/geocoder/cloudmade.py
# Copyright 2013, Trinity College Computing Center
# Last modified: 14 January 2012

import json
from geocoder_base import GeocoderBase, GeocoderResult, GeocoderError

# See http://developers.cloudmade.com/wiki/geocoding-http-api/Documentation
class GeocoderCloudmade(GeocoderBase):
	def __init__(self):
		self.url_server = "geocoding.cloudmade.com"
		self.url_path = "/535421843b58468485c05ec7eafc3f41/geocoding/v2/find.geojs"
		self.delay = 1.0	# one request per second

	# Given a street address, try to find the latitude and longitude.
	def FindAddr(self, address, countrycode=None):
		result = GeocoderResult(address, "Cloudmade")

		query = {
			'house':address[self.f_house_number],
			'street':address[self.f_street],
			'city':address[self.f_town],
			}
		if address[self.f_postal_code] != "":
			query['zipcode'] = address[self.f_postal_code]
		response = json.loads(self.get(self.url_path, {
			'query':";".join(map(lambda i: "%s:%s" % (i, query[i]), query.keys())),
			'return_location':'true',
			}))
		self.debug(json.dumps(response, indent=4, separators=(',', ': ')))


		if result.coordinates is None:
			self.debug("  No match")
		return result

	# It is worth caching the results of this geocoder?
	def should_cache(self):
		return True

#=============================================================================
# Tests
#=============================================================================
if __name__ == "__main__":

	geocoder = GeocoderCloudmade()
	geocoder.debug_enabled = True

	for address in (
		("99", "Falley Drive", "", "Westfield", "MA", "01085"),
		#("7", "Wandering Meadows Lane", "", "Wilbraham", "MA", "01095"),
		#("2071", "Riverdale Street", "", "West Springfield", "MA", "01089"),
		#("2071", "Riverdale Road", "", "West Springfield", "MA", "01089"),		# erroneous
		#("123", "Main Street", "", "Anytown", "ST", "00000"),
		):
		result = geocoder.FindAddr(address, countrycode="US")
		print result

