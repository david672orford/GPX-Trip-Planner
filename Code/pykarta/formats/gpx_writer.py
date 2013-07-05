#! /usr/bin/python
# Copyright 2012, Trinity College Computing Center
# Last modified: 25 January 2012

# Reference:
# * http://www.topografix.com/gpx.asp
#
# To validate output:
# xmllint --noout --schema http://www.topografix.com/GPX/1/1/gpx.xsd testfile.gpx

# Order required by schema is: wpt, rte, trk
# You must call write_*() in that order.

import string

class GpxSchemaOrderException(Exception):
	pass

class GpxWriter:

	def __init__(self, writable_object, creator):
		self.fh = writable_object
		self.fh.write('<?xml version="1.0"?>\n')
		self.fh.write('<gpx version="1.1"\n')
		self.fh.write(' creator="%s"\n' % creator)
		self.fh.write(' xmlns="http://www.topografix.com/GPX/1/1"\n')
		self.fh.write(' >\n')

		self.state = 0

	def __del__(self):
		self.fh.write("</gpx>\n")

	def encode(self, text):
		text = string.replace(text, '&', '&amp;')
		text = string.replace(text, '<', '&lt;')
		text = string.replace(text, '>', '&gt;')
		return text

	def write_wpt(self, lat, lon, **args):
		if self.state > 1:
			raise GpxSchemaOrderException
		self.state = 1
		self.fh.write("<wpt lat='%s' lon='%s'>\n" % (repr(lat), repr(lon)))
		for i in ("name", "desc", "cmt", "sym", "type"):
			if args.has_key(i):
				self.fh.write(" <%s>%s</%s>\n" % (i, self.encode(args[i]), i))
		self.fh.write("</wpt>\n")

	def write_rte(self, points, **args):
		if self.state > 2:
			raise GpxSchemaOrderException
		self.state = 2
		self.fh.write("<rte>\n")
		for i in ("name", "desc", "cmt"):
			if args.has_key(i):
				self.fh.write(" <%s>%s</%s>\n" % (i, self.encode(args[i]), i))
		for point in points:
			self.fh.write(" <rtept lat='%s' lon='%s'>\n" % (repr(point[0]), repr(point[1])))
			ptargs = point[2]
			for i in ("name", "desc", "cmt", "sym", "type"):
				if ptargs.has_key(i):
					self.fh.write("  <%s>%s</%s>\n" % (i, self.encode(ptargs[i]), i))
			self.fh.write(" </rtept>\n")
		self.fh.write("</rte>\n")

	def write_trk(self, points, **args):
		if self.state > 3:
			raise GpxSchemaOrderException
		self.state = 3
		self.fh.write("<trk>\n")
		for i in ("name", "desc", "cmt"):
			if args.has_key(i):
				self.fh.write(" <%s>%s</%s>\n" % (i, self.encode(args[i]), i))
		self.fh.write(" <trkseg>\n")
		for point in points:
			self.fh.write("  <trkpt lat='%s' lon='%s'></trkpt>\n" % (repr(point[0]), repr(point[1])))
		self.fh.write(" </trkseg>\n")
		self.fh.write("</trk>\n")

if __name__ == "__main__":
	import sys
	gpx = GpxWriter(sys.stdout, "GpxWriter test")
	gpx.write_wpt(42.0, -72.0, name='smith')
	gpx.write_rte([
		[42.0, -72.0],
		[43.0, -73.0],
		[44.0, -74.0]
		])

