#! /usr/bin/python
# geocoder_spreadsheet.py
# Copyright 2013, Trinity College Computing Center
# Last modified: 8 January 2013

import csv
import re
from fnmatch import fnmatch

from geocoder_base import GeocoderBase, GeocoderResult, GeocoderError

# This geocoder searches a single (hopefully small) spreadsheet which
# contains local overrides. It can be used to fix the geocoding of
# individual addresses until they can be inserted into OSM.
class GeocoderSpreadsheet(GeocoderBase):

	def FindAddr(self, address, countrycode=None):	# FIXME: countrycode is ignored
		result = GeocoderResult(address, "Spreadsheet")

		filename = "geocoder_exceptions.csv"
		try:
			self.debug("  Opening %s..." % filename)
			reader = csv.reader(open(filename, 'r'))
		except IOError:
			self.debug("  Spreadsheet not found")
			return result

		for row in reader:
			# row: 0=state, 1=town, 2=street, 3=house, 4=apartment, 5=lat, 6=lon, 7=precision
			if address[4] == row[0] \
					and address[self.f_state] == row[0] \
					and address[self.f_town] == row[1] \
					and address[self.f_street] == row[2] \
					and address[self.f_house_number] == row[3] \
					and ( address[self.f_apartment] == row[4] or fnmatch(address[self.f_apartment], row[4])):
				self.debug("  Match")

				try:
					# Parse latitude
					m = re.search("^N(\d+)d([0-9\.]+)'$", row[5])
					if m:
						row[5] = repr(float(m.group(1)) + float(m.group(2)) / 60.0)
					elif re.search("^[0-9\.-]+$", row[5]):
						row[5] = float(row[5])
					else:
						raise Exception

					# Parse longitude
					m = re.search("^W(\d+)d([0-9\.]+)'$", row[6])
					if m:
						row[6] = repr(0 - float(m.group(1)) - float(m.group(2)) / 60.0)
					elif re.search("^[0-9\.-]+$", row[6]):
						row[6] = float(row[6])
					else:
						raise Exception

					result.coordinates = (row[5], row[6])
					result.precision = row[7]
					break
				except:
					pass

		if result.coordinates is None:
			self.debug("  No match")
		return result

