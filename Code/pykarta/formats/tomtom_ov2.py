#! /usr/bin/python
# format_tomtom_ov2.py
# Copyright 2012, Trinity College Computing Center
# Last modified: 26 February 2012

import struct

class Ov2Error(Exception):
	pass

class Ov2POI:
	def __init__(self, lat, lon, description):
		self.lat = lat
		self.lon = lon
		self.description = description

	def len_in_bytes(self):
		return 14 + len(self.description)

	def write(self, fh):
		fh.write(struct.pack("<BIii%ds" % (len(self.description) + 1),
			2,
			self.len_in_bytes(),
			int(round(self.lon * 100000.0)),
			int(round(self.lat * 100000.0)),
			self.description
			))

class Ov2Reader:
	def __init__(self, filename):
		self.file = open(filename, "rb")
		self.pois = []
		self.parse()
		self.file.close()

	def read_or_die(self, bytecount):
		data = self.file.read(bytecount)
		if len(data) != bytecount:
			raise Ov2Error("truncated file")
		return data

	def read_word(self):
		data = self.read_or_die(4)
		return struct.unpack("<I", data)[0]

	def read_degrees(self):
		data = self.read_or_die(4)
		word = struct.unpack("<i", data)[0]
		return word / 100000.0

	def parse(self):
		while True:
			record_offset = self.file.tell()
			record_type = self.file.read(1)
			if record_type == "":
				break
			record_type = struct.unpack("B", record_type)[0]

			record_length = self.read_word()
			print "%d: Type: %d, Length: %d" % (record_offset, record_type, record_length)
			record_length -= 5
	
			# "Skipper" record	
			if record_type == 1:
				# Documentation from Tomtom has this backwards.
				ne_lon = self.read_degrees()
				ne_lat = self.read_degrees()
				sw_lon = self.read_degrees()
				sw_lat = self.read_degrees()
				print "    (%f, %f), (%f, %f)" % (sw_lat, sw_lon, ne_lat, ne_lon)
				print "    Not skipping."

			# POI
			elif record_type == 2 or record_type == 3:
				lon = self.read_degrees()
				lat = self.read_degrees()
				record_length -= 8
				data = self.read_or_die(record_length)
				name = data.partition('\0')[0]
				print "    (%f, %f)" % (lat, lon)
				print "    %s" % name
				self.pois.append(Ov2POI(lat, lon, name))
	
			# Unrecognized record type	
			else:
				print "   Skipping %d bytes." % record_length
				self.file.seek(record_length, 1)

class Ov2Splitter:
	def __init__(self, pois, minlat, minlon, maxlat, maxlon):
		#print "(%f, %f), (%f, %f)" % (minlat, minlon, maxlat, maxlon)

		self.minlat = minlat
		self.minlon = minlon
		self.maxlat = maxlat
		self.maxlon = maxlon

		self.pois = None
		self.child1 = None
		self.child2 = None

		if len(pois) < 25:								# doesn't need to be split
			self.pois = pois
		elif (maxlat - minlat) > (maxlon - minlon):		# bigger north-to-south
			pois.sort(key=lambda poi: poi.lat)
			middle = int(len(pois) / 2)
			self.child1 = Ov2Splitter(pois[0:middle], minlat, minlon, pois[middle].lat, maxlon)
			self.child2 = Ov2Splitter(pois[middle:], pois[middle].lat, minlon, maxlat, maxlon)
		else:											# bigger east-to-west
			pois.sort(key=lambda poi: poi.lon)
			middle = int(len(pois) / 2)
			self.child1 = Ov2Splitter(pois[0:middle], minlat, minlon, maxlat, pois[middle].lon)
			self.child2 = Ov2Splitter(pois[middle:], minlat, pois[middle].lon, maxlat, maxlon)

	def len_in_bytes(self):
		count = 21				# type byte and five four-byte words
		if self.pois:
			assert not self.child1 and not self.child2, "block contains both POIs and subblocks" 
			for poi in self.pois:
				count += poi.len_in_bytes()
		if self.child1:
			count += self.child1.len_in_bytes()
		if self.child2:
			count += self.child2.len_in_bytes()
		return count

	def write(self, fh):
		fh.write(struct.pack("<BIiiii",
			1,
			self.len_in_bytes(),
			int(round(self.maxlon * 100000.0)),
			int(round(self.maxlat * 100000.0)),
			int(round(self.minlon * 100000.0)),
			int(round(self.minlat * 100000.0))
			))
		if self.pois:
			for poi in self.pois:
				poi.write(fh)
		if self.child1:
			self.child1.write(fh)
		if self.child2:
			self.child2.write(fh)

class Ov2Writer:
	def __init__(self):
		self.pois = []
		self.minlat = 90.0
		self.minlon = 180.0
		self.maxlat = -90.0
		self.maxlon = -180.0

	def add_poi(self, poi):
		self.pois.append(poi)
		self.minlat = min(self.minlat, poi.lat)
		self.minlon = min(self.minlon, poi.lon)
		self.maxlat = max(self.maxlat, poi.lat)
		self.maxlon = max(self.maxlon, poi.lon)

	def write(self, fh):

		if self.minlat > self.maxlat or self.minlon > self.maxlon:
			raise Ov2Error("Incorrect usage: No POIs")

		# Simplistic implementation (without indexing)
		#for poi in self.pois:
		#	poi.write(self.file)

		# Sort, split, and generate index (skipper) records
		split = Ov2Splitter(self.pois, self.minlat, self.minlon, self.maxlat, self.maxlon)	
		split.write(fh)

if __name__ == "__main__":
	import sys

	if len(sys.argv) != 3:
		sys.stderr.write("Usage: tomtom_ov2.py in.ov2 out.ov2\n")
		sys.exit(1)
	(in_ov2, out_ov2) = sys.argv[1:]

	try:
		reader = Ov2Reader(in_ov2)
	
		writer = Ov2Writer()
		for poi in reader.pois:
			writer.add_poi(poi)
		fh = open(out_ov2, "wb")
		writer.write(fh)
	except Ov2Error as (message):
		sys.stderr.write("Ov2Error: %s\n" % message)


