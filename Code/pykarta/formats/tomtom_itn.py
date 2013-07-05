#! /usr/bin/python
# format_tomtom_itn.py
# Copyright 2012, Trinity College Computing Center
# Last modified: 16 March 2012

# See:
# http://www.tomtom.com/lib/doc/TomTomTips/index.html?itinerary_as_text_file.htm

class ItnPoint(object):
	def __init__(self, *args):
		self.lat, self.lon, self.description, self.stopover = args	
		self.description = self.description.replace("\r", " ").replace("\n", " ")

class ItnReader(object):
	def __init__(self, fh):
		self.fh = fh
		self.points = []
		for line in fh:
			line = line.split("|")
			if len(line) != 5:
				raise AssertionError("Corrupt ITN file")
			point = ItnPoint(int(line[1])/100000.0, int(line[0])/100000.0, line[2], int(line[3]) & 2)
			self.points.append(point)			
	def __iter__(self):
		for point in self.points:
			yield point

class ItnWriter(object):
	def __init__(self):
		self.points = []

	def add(self, point):
		if len(self.points) == 48:
			raise AssertionError("Too many route points")
		self.points.append(point)

	def write(self, fh):
		for i in range(len(self.points)):
			point = self.points[i]
			# See Tomtom SDK3 page 8 for a description of these codes
			if i == 0:								# first point
				flags = 4
			elif i == (len(self.points)-1):	# last point
				flags = 3
			elif point.stopover:
				flags = 3
			else:
				flags = 1
		
			fh.write("%d|%d|%s|%d|\n" % (
				int(point.lon * 100000),
				int(point.lat * 100000),
				point.description,
				flags))

if __name__ == "__main__":
	import sys
	writer = ItnWriter()
	writer.add(ItnPoint(42.00, -72.00, "Start", False))
	writer.add(ItnPoint(41.00, -72.00, "Middle", False))
	writer.add(ItnPoint(42.20, -72.00, "End", False))
	writer.write(sys.stdout)

	print "========================================"

	reader = ItnReader(sys.stdin)
	writer = ItnWriter()
	for point in reader.points:
		writer.add(ItnPoint(point.lat, point.lon, point.description, point.stopover))
	writer.write(sys.stdout)
	
