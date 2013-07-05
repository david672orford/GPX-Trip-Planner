# pykarta/geocoder/google.py
# Copyright 2013, Trinity College Computing Center
# Last modified: 13 June 2013

import string
import xml.etree.cElementTree as ET

from geocoder_base import GeocoderBase, GeocoderResult, GeocoderError

# See http://code.google.com/apis/maps/documentation/geocoding/index.html
class GeocoderGoogle(GeocoderBase):
	def __init__(self):
		self.url_server = "maps.google.com"
		self.url_path = "/maps/api/geocode/xml"
		self.delay = 0.2		# 5 requests per second

	# Send the query to the Google geocoder while taking care of
	# pacing the request rate.
	def query_google(self, query_hash):
		# HTTP query with retry
		while True:
			resp_text = self.get(self.url_path, query=query_hash)
			#print resp_text
			try:
				tree = ET.XML(resp_text)
			except:
				raise GeocoderError("Unparsable response")
	
			status = tree.find("status").text
			if status == "OVER_QUERY_LIMIT":		# too fast
				self.delay += 0.2					# slow down
				if self.delay > 10.0:
					raise GeocoderError("Google's daily query limit exceeded.")
			elif status == "ZERO_RESULTS":
				return None
			elif status != 'OK':
				raise GeocoderError("Geocoder failed: %s" % status)
			else:									# result received
				return tree

	xlate = {
		'street_number': 'house_number',
		'route': 'street',
		'administrative_area_level_1': 'state',
		'administrative_area_level_2': 'county',
		}

	location_types = {
		"ROOFTOP": "LOT",
		"RANGE_INTERPOLATED": "INTERPOLATED",
		}

	#-------------------------------------------------------------------
	# Given a street address, try to find the latitude and longitude.
	#-------------------------------------------------------------------
	def FindAddr(self, address, countrycode=None):
		result = GeocoderResult(address, "Google")

		# See: https://developers.google.com/maps/documentation/geocoding/
		query_hash = {
			'sensor': 'false',
			'address': "%s %s, %s, %s" \
				% (address[self.f_house_number], address[self.f_street],
				  address[self.f_town], address[self.f_state]),
			}
		components = []
		if countrycode != None:
			components.append("country:%s" % countrycode)
		if address[self.f_postal_code] != "":
			components.append("postal_code:%s" % address[self.f_postal_code])
		if len(components) > 0:
			query_hash['components'] = "|".join(components)

		tree = self.query_google(query_hash)
		if tree is not None:
			for item in tree.findall("result"):
				self.debug("  Candidate:")
	
				# Suck the address components into a hash and a list.
				found_addr_dict = {}
				found_addr_list = []
				for component in item.findall("address_component"):
					comp_type = component.find("type")
					if comp_type is None:	# ZIP+4?
						self.debug("    ZIP+4?")
						continue
					comp_type = comp_type.text
					comp_type = self.xlate.get(comp_type, comp_type)
					comp_name = component.find("short_name" if comp_type == "state" else "long_name").text
					self.debug("    %s: %s" % (comp_type, comp_name))

					found_addr_dict[comp_type] = comp_name
					found_addr_list.append([comp_type, comp_name])
				location_type = item.find("geometry/location_type").text
				self.debug("    location_type: %s" % location_type)
	
				if not self.result_truly_matches(address, found_addr_list):
					self.debug("  Partial match.")
					result.add_alternative_address(found_addr_dict)
					continue		# try next item
		
				if not location_type in self.location_types:
					self.debug("  Coordinate precision too low.")
					continue		# try next item

				# The answer has run the gauntlet! Use it.
				result.postal_code = found_addr_dict['postal_code']
				result.coordinates = (
					float(item.find("geometry/location/lat").text),
					float(item.find("geometry/location/lng").text),
					)
				result.precision = self.location_types[location_type]
				break
	
		if result.coordinates is None:
			self.debug("  No acceptable match found.")
		return result

	#-------------------------------------------------------------------
	# Given a town and state name, try to find information about it.
	#-------------------------------------------------------------------
	def FindTown(self, town, state, countrycode=None):
		query_hash = {
			'sensor': 'false',
			'address': "%s, %s" % (town, state)
			}
		components = []
		if countrycode != None:
			components.append("country:%s" % countrycode)
		if len(components) > 0:
			query_hash['components'] = "|".join(components)

		tree = self.query_google(query_hash)

		if tree == None:
			self.debug("  No match")
			return None

		county = None

		for result in tree.findall("result"):
			self.debug("  Candidate:")

			# Reject partial matches
			partial = result.find("partial_match")
			if partial != None and partial.text == "true":
				self.debug("  Partial match")
				continue

			for component in result.findall("address_component"):
				comp_type = component.find("type")
				if comp_type != None:		# why None? We don't know.
					comp_type = comp_type.text
				comp_name = component.find("long_name").text
				self.debug("  %s: %s" % (comp_type, comp_name))
				if comp_type == "administrative_area_level_2":		# county
					county = comp_name
					if county.split(" ")[-1] != "County":
						county = "%s County" % county

		return {
			'lat': float(result.find("geometry/location/lat").text),
			'lon': float(result.find("geometry/location/lng").text),
			'county': county
			}

	def should_cache(self):
		return True

