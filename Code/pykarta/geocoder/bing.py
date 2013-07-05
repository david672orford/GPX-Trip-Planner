# pykarta/geocoder/bing.py
# Copyright 2013, Trinity College Computing Center
# Last modified: 6 June 2013

import json
from geocoder_base import GeocoderBase, GeocoderResult, GeocoderError
from pykarta.address import split_house_street_apt

# See http://msdn.microsoft.com/en-us/library/ff701714.aspx
class GeocoderBing(GeocoderBase):
	def __init__(self):
		self.url_server = "dev.virtualearth.net"
		self.url_path = "/REST/v1/Locations"
		self.delay = 1.0	# one request per second
		self.api_key = 'AiMQM9AWZQuAHQ0UotcHHaWVvp3M1OPTGPtxLXNnXAe74Q4tL1PnF4R_vEIrQ_Ue'

	location_types = {
		'Parcel':'LOT',
		'InterpolationOffset':'INTERPOLATED',
		}

	# Given a street address, try to find the latitude and longitude.
	def FindAddr(self, address, countrycode=None):
		result = GeocoderResult(address, "Bing")

		query = {
			'countryRegion':countrycode,
			'adminDistrict':address[self.f_state],
			'locality':address[self.f_town],
			'addressLine':"%s %s" % (address[self.f_house_number], address[self.f_street]),
			}
		if address[self.f_postal_code] != "":
			query['postalCode'] = address[self.f_postal_code]
		query['includeNeighborhood'] = 1
		query['key'] = self.api_key

		response = json.loads(self.get(self.url_path, query=query))
		#self.debug(json.dumps(response, indent=4, separators=(',', ': ')))

		# FIXME: can there be more than one "resource"?
		try:
			response = response['resourceSets'][0]['resources'][0]
		except:
			response = None

		if response and response['confidence'] == 'High' and response['matchCodes'] == ['Good']:
			address1 = split_house_street_apt(response['address']['addressLine'])
			if address1 is not None:
				found_addr_list = []
				found_addr_list.append(("house_number", address1['House Number']))
				found_addr_list.append(("street", address1['Street']))
				found_addr_list.append(("town", response['address']['locality']))
				found_addr_list.append(("state", response['address']['adminDistrict']))
				#print found_addr_list
		
				if self.result_truly_matches(address, found_addr_list):
					location_type = response['geocodePoints'][0]['calculationMethod']
					lat, lon = response['geocodePoints'][0]['coordinates']
					if location_type in self.location_types:
						result.coordinates = (lat, lon)
						result.precision = self.location_types[location_type]

		if result.coordinates is None:
			self.debug("  No match")
		return result

	# It is worth caching the results of this geocoder?
	def should_cache(self):
		return True

