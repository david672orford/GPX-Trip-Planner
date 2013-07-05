# pykarta/geocoder/dst.py
# Copyright 2013, Trinity College Computing Center
# Last modified: 6 June 2013

import json
import urllib
import httplib
import time

from geocoder_base import GeocoderBase, GeocoderResult, GeocoderError
from pykarta.address import disabbreviate_street

# See http://www.datasciencetoolkit.org/developerdocs
class GeocoderDST(GeocoderBase):
	def __init__(self):
		self.url_server = "www.datasciencetoolkit.org"
		self.url_path = "/street2coordinates"
		self.delay = 1.0	# one request per second

	# Given a street address, try to find the latitude and longitude.
	def FindAddr(self, address, countrycode=None):
		result = GeocoderResult(address, "DST")

		query = "%s %s, %s, %s %s" \
				% (address[self.f_house_number], address[self.f_street],
				  address[self.f_town], address[self.f_state], address[self.f_postal_code])
		get_path = "%s/%s" % (self.url_path, urllib.quote_plus(query))

		# Run the query and close the connexion. If we don't close the connexion,
		# we get BadStatusLine next time. Presumably the server does not handle
		# persistent connexions correctly.
		response_text = self.get(get_path)
		self.conn = None

		response = json.loads(response_text)
		response = response[query]	# keyed by sought address
		self.debug(json.dumps(response, indent=4, separators=(',', ': ')))

		if response is not None and response['street_number'] is not None:
			found_addr_list = (
				('house_number',response['street_number']),
				('street',disabbreviate_street(response['street_name'])),
				('town',response['locality']),
				('state',response['region']),
				)
			#if response['confidence'] == 1.0:
			if self.result_truly_matches(address, found_addr_list):
				result.coordinates = (response['latitude'], response['longitude'])
				result.precision = "INTERPOLATED"
			else:
				result.alternative_addresses.append(", ".join(map(lambda i: response[i], ("street_number","street_name","locality","region"))))

		if result.coordinates is None:
			self.debug("  No match")
		return result

	# It is worth caching the results of this geocoder?
	def should_cache(self):
		return True

