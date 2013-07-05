#! /usr/bin/python
# pykarta/geocoder/multi.py
# Copyright 2013, Trinity College Computing Center
# Last modified: 15 January 2013

import os
from pykarta.misc import file_age_in_days, get_cachedir
from geocoder_base import GeocoderBase, GeocoderResult, GeocoderError

# Import the geocoders
from spreadsheet import GeocoderSpreadsheet
from nominatim import GeocoderNominatim
from google import GeocoderGoogle
from dst import GeocoderDST
from bing import GeocoderBing

#=============================================================================
# This geocoder is a wrapper for a list of actual geocoders. It calls them
# in sequence until one of them finds the requested information.
# It also implements caching of results.
#=============================================================================
class GeocoderMulti(GeocoderBase):

	def __init__(self):
		self.cache = GeocoderCache()
		self.geocoders = [
			GeocoderSpreadsheet(),
			GeocoderNominatim(),
			GeocoderBing(),
			GeocoderGoogle(),
			GeocoderDST(),
			]

	# Query the geocoders and cache the answers
	def FindAddr(self, address, countrycode=None):
		self.debug("======== %s ========" % address)

		result = self.cache.FindAddr(address, countrycode=countrycode)
		if result.coordinates is not None:
			return result

		result = GeocoderResult(address, "None")
		should_cache = False

		# Run each geocoder in turn until we find a match
		for geocoder in self.geocoders:
			self.debug("Trying:", geocoder.__class__.__name__)
			iresult = geocoder.FindAddr(address, countrycode=countrycode)
			if iresult.coordinates is not None:
				result.postal_code = iresult.postal_code
				result.coordinates = iresult.coordinates
				result.precision = iresult.precision
				result.source = iresult.source
				should_cache = geocoder.should_cache()
				if iresult.precision != "INTERPOLATED":
					break		# good enough
			else:
				result.alternative_addresses.extend(iresult.alternative_addresses)

		# Store the result.
		if should_cache:
			self.cache.store(result)

		self.debug("\n")
		return result

	def FindAddrAll(self, address, countrycode=None):
		results = []
		for geocoder in self.geocoders:
			self.debug("====================================================")
			self.debug("Trying:", geocoder.__class__.__name__)
			result = geocoder.FindAddr(address, countrycode=countrycode)
			if result.coordinates is not None:
				results.append(result)
		return results

#=============================================================================
# This geocoder is used to return results from the cache.
#=============================================================================
class GeocoderCache(GeocoderBase):

	def __init__(self):
		self.cachedir = os.path.join(get_cachedir(), "geocoder")
		if not os.path.exists(self.cachedir):
			os.makedirs(self.cachedir)	

	def cachefile_name(self, address):
		formated_address = "%s %s, %s, %s %s" \
			% (address[self.f_house_number], address[self.f_street],
			  address[self.f_town], address[self.f_state], address[self.f_postal_code]
			)
		return "%s/%s" % (self.cachedir, formated_address.replace("/", "_"))

	def FindAddr(self, address, countrycode=None):	# FIXME: countrycode is ignored
		result = GeocoderResult(address, "Cache")

		cachefile_name = self.cachefile_name(address)
		cachefile_age = file_age_in_days(cachefile_name)
		if cachefile_age and cachefile_age < 30:
			fh = open(cachefile_name, "r")
			cached_answer = fh.read()
			fh.close()
			self.debug("  Using %.1f day old answer from cache." % cachefile_age)
			try:
				lines = cached_answer.splitlines()
				if len(lines) != 1:
					raise AssertionError
				lat, lon, result.precision, result.source = lines[0].split(",")
				result.coordinates = (float(lat), float(lon))
			except:
				self.debug("  Bad cache entry")

		if result.coordinates is None:
			self.debug("  No match")
		return result

	def store(self, result):
		cachefile = open(self.cachefile_name(result.query_address), "w")
		if result:	
			self.debug("  Storing new result in cache.")
			cachefile.write("%s,%s,%s,%s\n" % (repr(result.coordinates[0]), repr(result.coordinates[1]), result.precision, result.source))
		else:
			self.debug("  Storing empty result in cache.")
		cachefile.close()

#=============================================================================
# Test
#=============================================================================
if __name__ == "__main__":
	import csv
	from pykarta.formats.gpx_writer import GpxWriter

	reader = csv.reader(open("test.csv","r"))
	writer = GpxWriter(open("test.gpx","w"), "Geocoder Test")

	geocoder = GeocoderMulti()
	geocoder.debug_enabled = True

	for address in reader:
		for result in geocoder.FindAddrAll(address, countrycode="US"):
			writer.write_wpt(
				result.coordinates[0], result.coordinates[1],
				name="%s %s (%s)" % (address[0], address[1], result.source),
				sym="Pin, Red",
				)



