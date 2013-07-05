#! /usr/bin/python
# format_kml_writer.py
# Copyright 2011, Trinity College Computing Center
# Written by David Chappell
# Last modified: 24 September 2011

import string

class KmlWriter:

	def __init__(self, writable_object, creator):
		self.fh = writable_object
		self.fh.write("""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://earth.google.com/kml/2.2">
<Document>
<Style id="border">
 <PolyStyle>
  <color>260099FF</color>
  <fill>1</fill>
  <outline>1</outline>
 </PolyStyle>
</Style>
<Style id="green">
 <IconStyle><Icon><href>http://maps.google.com/mapfiles/kml/pushpin/grn-pushpin.png</href></Icon></IconStyle>
 <LabelStyle><scale>0.25</scale></LabelStyle>
</Style>
<Style id="red">
 <IconStyle><Icon><href>http://maps.google.com/mapfiles/kml/pushpin/red-pushpin.png</href></Icon></IconStyle>
 <LabelStyle><scale>0.25</scale></LabelStyle>
</Style>
""")

	def __del__(self):
		self.fh.write('</Document>\n')
		self.fh.write("</kml>\n")

	def encode(self, text):
		text = string.replace(text, '&', '&amp;')
		text = string.replace(text, '<', '&lt;')
		text = string.replace(text, '>', '&gt;')
		return text

	def write_poi(self, lat, lon, **args):
		self.fh.write("<Placemark>\n")
		for i in ("name", "description", "styleUrl"):
			if args.has_key(i):
				self.fh.write(" <%s>%s</%s>\n" % (i, self.encode(args[i]), i))
		self.fh.write(" <Point><coordinates>%s,%s</coordinates></Point>\n" % (repr(lon), repr(lat)))
		self.fh.write("</Placemark>\n")

	def write_polygon(self, points, **args):
		self.fh.write("<Placemark>\n")
		for i in ("name", "description"):
			if args.has_key(i):
				self.fh.write(" <%s>%s</%s>\n" % (i, self.encode(args[i]), i))
		self.fh.write("<styleUrl>#border</styleUrl>\n")
		self.fh.write(" <Polygon>\n")
		self.fh.write("  <outerBoundaryIs>\n")
		self.fh.write("   <LinearRing>\n")
		self.fh.write("    <coordinates>")
		for point in points:
			self.fh.write(" %s,%s\n" % (repr(point[1]), repr(point[0])))
		self.fh.write("    </coordinates>\n")
		self.fh.write("   </LinearRing>\n")
		self.fh.write("  </outerBoundaryIs>\n")
		self.fh.write(" </Polygon>\n")
		self.fh.write("</Placemark>\n")

if __name__ == "__main__":
	import sys
	kml = KmlWriter(sys.stdout, "KmlWriter test")
	kml.write_poi(42.0, -72.0, name='smith')
	kml.write_polygon([
		[42.0, -72.0],
		[43.0, -73.0],
		[44.0, -74.0]
		])

