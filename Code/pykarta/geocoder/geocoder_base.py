# pykarta/geocoder/geocoder_base.py
# Copyright 2013, Trinity College Computing Center
# Last modified: 6 June 2013

import httplib
import socket
import urllib
import time
import sys
import string
from pykarta.misc import NoInet

class GeocoderBase:

	# Offsets into the address array passed to FindAddr()
	f_house_number = 0
	f_street = 1
	f_apartment = 2
	f_town = 3
	f_state = 4
	f_postal_code = 5

	conn = None
	debug_enabled = True

	def debug(self, *args):
		if self.debug_enabled:
			string_list = []
			for i in args:
				string_list.append(i)
			sys.stderr.write(string.join(string_list, " "))
			sys.stderr.write("\n")

	# Send an HTTP query to the geocoder server
	# Set self.url_server and self.delay before calling
	def get(self, path, query=None):
		if self.conn is None:
			self.debug("  Opening HTTP connexion...")
			self.conn = httplib.HTTPConnection(self.url_server)
		try:
			if query is not None:
				path = path + "?" + urllib.urlencode(query)
			self.debug("  GET %s" % path)
			self.conn.request("GET", path)
			time.sleep(self.delay)

			http_resp = self.conn.getresponse()
			self.debug("    %s %s" % (http_resp.status, http_resp.reason))
			if http_resp.status != 200:
				raise GeocoderError("HTTP GET failed")

			resp_text = http_resp.read()
			if resp_text == "":
				raise GeocoderError("Empty HTTP response")

			return resp_text

		except socket.gaierror:		# address-related error
			raise NoInet

	def result_truly_matches(self, address, reply_address_components):
		to_find = (
			('house_number', address[self.f_house_number]),
			('street', address[self.f_street]),
			(None, address[self.f_town]),
			('state', address[self.f_state]),
			)
		find_in = list(reply_address_components)[:]
		#self.debug("Find %s in %s" % (str(to_find), str(find_in)))
		for find_name, find_value in to_find:
			#self.debug("Searching for %s %s..." % (find_name, find_value))
			while True:
				if len(find_in) == 0:
					return False
				next_name, next_value = find_in.pop(0)
				#self.debug(" %s %s" % (next_name, next_value))
				if (find_name is None or next_name == find_name) and next_value == find_value:
					break	
		return True		

	def result_town_matches(self, town, reply_address_components):
		for name, value in reply_address_components:
			if value == town:
				return True
		return False

	#--------------------------------------------------------------
	# Override these in derived classes
	#--------------------------------------------------------------

	def FindAddr(self, address, countrycode=None):
		raise GeocoderUnimplemented

	def FindStreet(self, street, town, state, countrycode=None):
		raise GeocoderUnimplemented

	def FindTown(self, town, state, countrycode=None):
		raise GeocoderUnimplemented

	def Reverse(self, lat, lon, countrycode=None):
		raise GeocoderUnimplemented

	# Override to return True in slow geocoders.
	def should_cache(self):
		return False

# What a geocoder returns
class GeocoderResult(object):
	def __init__(self, query_address, source):
		self.query_address = query_address
		self.postal_code = None
		self.coordinates = None
		self.precision = None
		self.source = source
		self.alternative_addresses = []
	def __str__(self):
		return ",".join(map(lambda i: "%s:%s" % (i, str(getattr(self,i))), vars(self)))
	def add_alternative_address(self, address_dict):
		alt_addr = []
		for i in ("house_number", "street", "sublocality", "locality", "town", "city", "state", "postal_code"):
			if i in address_dict:
				alt_addr.append(address_dict[i])
		self.alternative_addresses.append(", ".join(alt_addr))

# Geocoders throw this for most errors.
class GeocoderError(Exception):
	pass

# For methods which a particular geocoder does not implement.
class GeocoderUnimplemented(GeocoderError):
	pass


