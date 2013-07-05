#! /usr/bin/python
# encoding=utf-8
# pykarta/geometry/__init__.py
# Copyright 2013, Trinity College
# Last modified: 20 June 2013

import math
import re

#=============================================================================
# Point
#=============================================================================

# We already have a lot of functions which require that points fed to them
# as input be expressed as a [lat, lon] array. However, we are more and
# more using point objects with lat and lon attributes. We will convert
# functions which return points to return these objects which can be
# consumed by both old and new functions.
class Point(object):
	__slots__ = ['lat', 'lon']
	def __init__(self, *args):
		if len(args) == 0:			# Point()
			self.lat = None
			self.lon = None
		elif len(args) == 1:		# Point(point)
			self.lat = args[0][0]
			self.lon = args[0][1]
		elif len(args) == 2:		# Point(lat, lon)
			self.lat = args[0]
			self.lon = args[1]
		else:
			raise Exception("Invalid arguments:", args)

	def __str__(self):
		return "(%f,%f)" % (self.lat, self.lon)

	# This is what allows old functions to consume these objects.
	def __getitem__(self, index):
		if index == 0:
			return self.lat
		elif index == 1:
			return self.lon
		else:
			raise IndexError

# Convert an array of points (presumably expressed as (lat, lon) to Point objects.
def Points(points):
	return map(Point, points)

#=============================================================================
# Coordinate formatting
#=============================================================================

# Convert a latitude and longitude in decimal degrees to a degrees, minutes and seconds.
def dms_lat_lon(lat, lon):
	return (
		u"%s%02d°%02d'%04.1f\"" % dms_split(lat, "N", "S"),
		u"%s%03d°%02d'%04.1f\"" % dms_split(lon, "E", "W")
		)

def dms_split(degrees, positive, negative):
	hemisphere = positive if degrees > 0.0 else negative
	degrees = abs(degrees)
	minutes,seconds = divmod(degrees*3600,60)
	degrees,minutes = divmod(minutes,60)
	return (hemisphere, degrees, minutes, seconds)

# Convert a latitude and longitude in decimal degrees to a degrees, minutes with decimal point.
def dm_lat_lon(lat, lon):
	return (
		u"%s%02d°%06.3f'" % dm_split(lat, "N", "S"),
		u"%s%03d°%06.3f'" % dm_split(lon, "E", "W")
		)

def dm_split(degrees, positive, negative):
	hemisphere = positive if degrees > 0.0 else negative
	degrees = abs(degrees)
	degrees,minutes = divmod(degrees*60,60)
	return (hemisphere, degrees, minutes)

#=============================================================================
# Coordinate parsing
#=============================================================================

# From Wikipedia article Whitehouse: 38° 53′ 51.61″ N, 77° 2′ 11.58″ W
# \u2032 -- prime (minutes sign)
# \u2033 -- double prime (seconds sign)
# \u2019 -- single closing quote
# \u201d -- double closing quote
def parse_lat_lon(coords_text):
	if not re.search(u'^[\(\-0-9\.°\'\u2019\u2032"\u201d\u2033NSEW, \)]+$', coords_text, flags=re.IGNORECASE):
		return (None, None)

	print "Pasted coordinates:", coords_text

	# Make more standard
	coords_text = coords_text.upper()
	coords_text = coords_text.replace(u"(", u"")
	coords_text = coords_text.replace(u")", u"")
	coords_text = coords_text.replace(u" ", u"")				# remove spaces
	coords_text = coords_text.replace(u"'", u"\u2032")		# ASCII single quote (apostroph) to prime
	coords_text = coords_text.replace(u"\u2019", u"\u2032")	# right single quote to prime
	coords_text = coords_text.replace(u'"', u'\u2033')		# ASCII double quote to double prime
	coords_text = coords_text.replace(u'\u201d', u'\u2033')	# right double quote to double prime

	words = _split_coords_text(coords_text)
	lat = _parse_degrees(words[0], "NS")
	lon = _parse_degrees(words[1], "EW")
	return (lat, lon)

def _split_coords_text(coords_text):
	m = re.match('^([^,]+),([^,]+)$', coords_text)
	if m:
		return (m.group(1), m.group(2))

	m = re.match('^([NS].+)([EW].+)$', coords_text)
	if m:
		return (m.group(1), m.group(2))

	m = re.match('^(.+[NS])(.+[EW])$', coords_text)
	if m:
		return (m.group(1), m.group(2))

	raise Exception("Two coordinates required")

def _parse_degrees(degrees_string, directions):
	sign = 1.0
	if directions[0] in degrees_string:		# N or E
		degrees_string = degrees_string.replace(directions[0], "")
	elif directions[1] in degrees_string:	# S or W
		degrees_string = degrees_string.replace(directions[1], "")
		sign = -1.0

	# Decimal degrees signed
	m = re.search(u'^([-\d\.]+)°?$', degrees_string)
	if m:
		return float(m.group(1)) * sign

	# Degrees, minutes, seconds
	m = re.search(u'^(\d+)°(\d+)\u2032([\d\.]+)\u2033$', degrees_string)
	if m:
		degrees = int(m.group(1))
		degrees += int(m.group(2)) / 60.0
		degrees += float(m.group(3)) / 3600.0
		return degrees * sign

	m = re.search(u'^(\d+)°([\d\.]+)\u2032?$', degrees_string)
	if m:
		degrees = int(m.group(1))
		degrees += float(m.group(2)) / 60.0
		return degrees * sign

	raise Exception("Failed to parse coordinate: %s" % degrees_string)

#=============================================================================
# Bounding Box Object
#=============================================================================

# This object is used when we need to create or manipulate bounding boxes.
#
# Some of our classes use this internally. However, we generally pass bounding
# boxes around as an array of four numbers: (top, left, bottom, right). This
# is the order used by the Osmgpsmap widget.
class BoundingBox(object):
	def __init__(self, init=None):
		if init is None:
			self.reset()
		elif isinstance(init, BoundingBox):
			self.min_lat = init.min_lat
			self.max_lat = init.max_lat
			self.min_lon = init.min_lon
			self.max_lon = init.max_lon
			self.valid = init.valid
		elif len(init) == 4:
			# Order used by Openlayers
			self.min_lon, self.min_lat, self.max_lon, self.max_lat = init
			self.valid = True
		else:
			raise ValueError

	def reset(self):
		self.min_lat = None
		self.max_lat = None
		self.min_lon = None
		self.max_lon = None
		self.valid = False

	def __str__(self):
		if self.valid:
			return "min_lon=%f max_lon=%f min_lat=%f, max_lat=%f" % (self.min_lon, self.max_lon, self.min_lat, self.max_lat)
		else:
			return "<invalid>"

	# Used only by Openlayers border editor
	def as_rectangle(self):
		if self.valid:
			return (
				Point(self.min_lat, self.min_lon),	# bottom left
				Point(self.min_lat, self.max_lon),	# bottom right
				Point(self.max_lat, self.max_lon),	# top right
				Point(self.max_lat, self.min_lon),	# top left
				Point(self.min_lat, self.min_lon),	# bottom left again
				)
		else:
			return None

	def as_polygon(self):
		if self.valid:
			return Polygon((
				Point(self.min_lat, self.min_lon),	# bottom left
				Point(self.min_lat, self.max_lon),	# bottom right
				Point(self.max_lat, self.max_lon),	# top right
				Point(self.max_lat, self.min_lon),	# top left
				))
		else:
			return None

	def _go_valid(self):
		if not self.valid:
			self.min_lat = 90
			self.max_lat = -90
			self.min_lon = 180
			self.max_lon = -180
			self.valid = True

	def add_point(self, point):
		self._go_valid()
		self.min_lat = min(self.min_lat, point.lat)
		self.max_lat = max(self.max_lat, point.lat)
		self.min_lon = min(self.min_lon, point.lon)
		self.max_lon = max(self.max_lon, point.lon)

	def add_points(self, points):
		for point in points:
			self.add_point(point)

	def add_bbox(self, bbox):
		if not isinstance(bbox, BoundingBox): raise TypeError
		self._go_valid()
		self.min_lat = min(self.min_lat, bbox.min_lat)		
		self.max_lat = max(self.max_lat, bbox.max_lat)		
		self.min_lon = min(self.min_lon, bbox.min_lon)		
		self.max_lon = max(self.max_lon, bbox.max_lon)		

	# Return the point at the center of the bounding box.
	def center(self):
		if self.valid:
			return Point( (self.max_lat + self.min_lat) / 2, (self.max_lon + self.min_lon) / 2 )
		else:
			return None

	# Does the bounding box contain the indicated point?
	def contains_point(self, point):
		return (point.lat >= self.min_lat and point.lat <= self.max_lat and point.lon >= self.min_lon and point.lon <= self.max_lon)

	# Do the bounding boxes overlap?
	def overlaps(self, other):
		if self.valid and other.valid:
			# See: http://rbrundritt.wordpress.com/2009/10/03/determining-if-two-bounding-boxes-overlap/
			# Distance between centers on horizontal and vertical axes

			#rabx = abs(self.min_lon + self.max_lon - b_left - b_right)
			rabx = abs(self.min_lon + self.max_lon - other.min_lon - other.max_lon)

			#raby = abs(self.max_lat + self.min_lat - b_top - b_bottom)
			raby = abs(self.max_lat + self.min_lat - other.max_lat - other.min_lat)

			# Sums of radii on horizontal and vertical axes
			#raxPrbx = self.max_lon - self.min_lon + b_right - b_left
			raxPrbx = self.max_lon - self.min_lon + other.max_lon - other.min_lon

			#rayPrby = self.max_lat - self.min_lat + b_top - b_bottom
			rayPrby = self.max_lat - self.min_lat + other.max_lat - other.min_lat

			if rabx <= raxPrbx and raby <= rayPrby:
				return True
		return False

	# Expand (or theoretically shrink) the bounding box around its center.
	# We used this to leave extra space around the enclosed objects.
	def scale(self, factor):
		if self.valid:
			scaled_half_width = (self.max_lon - self.min_lon) * factor / 2.0
			scaled_half_height = (self.max_lat - self.min_lat) * factor / 2.0
			center_lat, center_lon = self.center()
			self.min_lat = center_lat - scaled_half_height
			self.max_lat = center_lat + scaled_half_height
			self.min_lon = center_lon - scaled_half_width
			self.max_lon = center_lon + scaled_half_width

#=============================================================================
# Route
#=============================================================================
class Route(object):
	def __init__(self, points):
		self.points = points
		self.distances = []
		self.bearings = []
		for i in range(len(self.points) - 1):
			p1 = self.points[i]
			p2 = self.points[i+1]
			self.distances.append(points_distance_pythagorian(p1, p2))
			self.bearings.append(points_bearing(p1, p2))

	def routeDistance(self, poi_point, debug=False):
		running_route_distance = 0
		closest_excursion_distance = None		# distance to closest (possibly extended) route segment
		closest_route_distance = None			# distance from start if above turns out to be closest

		# Step through the segments of this route.
		# self.points[i] -- the current point
		# self.bearings[i] -- the direction of the route segment which starts here
		# self.distances[i] -- the length of the route segment which starts here
		for i in range(len(self.points) - 1):

			# Bearing in degrees of corse from current point to this house
			house_bearing = points_bearing(self.points[i], poi_point)

			# Link of direct line from current point to house
			# We will use this as the hypotenus of a right triangle. The adjacent side
			# will run along the route segment that starts at the current point (though
			# it may extend furthur).
			house_hyp_length = points_distance_pythagorian(self.points[i], poi_point)

			# The angle in degrees between the route segment that starts at this point
			# and the direct line to the house from this point
			relative_bearing = (house_bearing - self.bearings[i] + 360) % 360

			if debug:
				print "  From point %d house is at %f degrees, %f meters away." % (i, house_bearing, house_hyp_length)
				print "    Relative bearing %f degrees" % (relative_bearing)

			# If the direct line to the house does not point behind us,
			if relative_bearing <= 90.0 or relative_bearing >= 270.0:

				# Compute the lengths of the sides of the right triangle. We do not
				# care on which side of the route the house lies.
				relative_bearing_radians = math.radians(relative_bearing)
				opposite = math.fabs(house_hyp_length * math.sin(relative_bearing_radians))
				adjacent = math.fabs(house_hyp_length * math.cos(relative_bearing_radians))

				# How far will we need to move off of the route to read the house?
				# We do not know where the road to the house lies, so we use
				# an arbitrary route.
				# We start with the amount that the house is off to one side.
				# If it lies beyond the end of the current segment, we add the 
				# amount by which we would need to extend the segment in order
				# to reach it.
				excursion = opposite
				if adjacent > self.distances[i]:
					excursion += (adjacent - self.distances[i])
				if debug:
					print "    Opposite %f meters" % (opposite)
					print "    Adjacent %f meters" % (adjacent)
					print "    Excursion %f meters" % (excursion)

				# If the excursion from the route is the smallest yet, save it.
				if not closest_excursion_distance or excursion < closest_excursion_distance:
					closest_excursion_distance = excursion
					# The distance to the house is the length of all route segments
					# that are already behind us plus the distance from this point 
					# of the point where we would leave the route in order to reach
					# the house.
					closest_route_distance = running_route_distance + min(adjacent, self.distances[i])
					if debug:
						print "    (Closest yet at %f meters)" % closest_route_distance

			# Keep a running total of the length of route segments that are behind us.
			running_route_distance += self.distances[i]

		return closest_route_distance		# may be None

#=============================================================================
# A string of points
#=============================================================================
class LineString(object):
	def __init__(self, points):
		self.points = list(points)		# copies and makes mutable
		self.bbox = None
	def get_bbox(self):
		if self.bbox is None:
			self.bbox = BoundingBox()
			self.bbox.add_points(self.points)
		return self.bbox

#=============================================================================
# Simple (no holes) Polygons
#
# The first point should not be repeated. The polygon is assumed to be closed.
#
# All of the calculations assume a rectangular grid. In other words, they
# ignore projection.
#=============================================================================

class Polygon(LineString):

	# Methods area() and centroid() came from:
	# http://local.wasp.uwa.edu.au/~pbourke/geometry/polyarea/
	# We have shortened them up.
	def area(self):
		area=0
		j=len(self.points)-1
		for i in range(len(self.points)):
			p1=self.points[i]
			p2=self.points[j]
			area+= (p1[0]*p2[1])
			area-=p1[1]*p2[0]
			j=i
		area/=2;
		return area;

	def centroid(self):
		x=0
		y=0
		j=len(self.points)-1;
		for i in range(len(self.points)):
			p1=self.points[i]
			p2=self.points[j]
			f=p1[0]*p2[1]-p2[0]*p1[1]
			x+=(p1[0]+p2[0])*f
			y+=(p1[1]+p2[1])*f
			j=i
		f=self.area()*6
		return (x/f,y/f)

	# See:
	# http://www.faqs.org/faqs/graphics/algorithms-faq/ (section 2.03)
	# http://www.ecse.rpi.edu/Homepages/wrf/Research/Short_Notes/pnpoly.html
	def contains_point(self, testpt):
		if not self.get_bbox().contains_point(testpt):
			return False

		inPoly = False
		i = 0
		j = len(self.points) - 1
		while i < len(self.points):
			verti = self.points[i]
			vertj = self.points[j]
			if ( ((verti.lat > testpt.lat) != (vertj.lat > testpt.lat)) \
					and \
					(testpt.lon < (vertj.lon - verti.lon) * (testpt.lat - verti.lat) / (vertj.lat - verti.lat) + verti.lon) ):
				inPoly = not inPoly
			j = i
			i += 1

		return inPoly

	# Try 81 possible label positions starting just inside the polygon's
	# bounding box. Return the one which is farthest from the polygon's
	# border.
	def choose_label_center(self):
		bbox = self.get_bbox()
		lat_step = (bbox.max_lat - bbox.min_lat) / 10.0
		lon_step = (bbox.max_lon - bbox.min_lon) / 10.0
		largest_distance = 0
		largest_distance_point = None
		for y in range(1,10):
			lat = bbox.min_lat + lat_step * y
			for x in range(1,10):
				lon = bbox.min_lon + lon_step * x
				point = Point(lat, lon)
				if self.contains_point(point):
					distance = self.distance_to(point, largest_distance)
					if distance is not None and distance > largest_distance:
						largest_distance = distance
						largest_distance_point = point
		return largest_distance_point

	def distance_to(self, point, low_abort=None):
		shortest = None
		i = 0
		while i < len(self.points):
			p1 = self.points[i]
			p2 = self.points[(i+1) % len(self.points)]
			distance = plane_lineseg_distance(point, p1, p2)
			if shortest is None or distance < shortest:
				shortest = distance
			if low_abort is not None and distance < low_abort:
				return None
			i += 1
		return shortest

#=============================================================================
# Distances on a plane
# (This is used for label placement.)
# See: http://blog.csharphelper.com/2010/03/26/find-the-shortest-distance-between-a-point-and-a-line-segment-in-c.aspx
#=============================================================================

# Distance between two points
def plane_points_distance(p1, p2):
	dx = p1[0] - p2[0]
	dy = p1[1] - p2[1]
	return math.sqrt(dx * dx + dy * dy)

# Distance of a point to a line segment
def plane_lineseg_distance(pt, p1, p2):
	dx = p2[0] - p1[0]
	dy = p2[1] - p1[1]

	# Zero-length line segment?
	if dx == 0.0 or dy == 0.0:
		return plane_points_distance(p1, pt)

	# How far along the line segment is the closest point?
	# 0.0 means it is opposite p1
	# 1.0 means it is opposite p2
	t = ((pt[0] - p1[0]) * dx + (pt[1] - p1[1]) * dy) / (dx * dx + dy * dy)

	if t < 0.0:		# before start point?
		return plane_points_distance(p1, pt)
	elif t > 1.0:	# after end point?
		return plane_points_distance(p2, pt)
	else:
		closest = (p1[0] + t * dx, p1[1] + t * dy);
		return plane_points_distance(closest, pt)

#=============================================================================
# Distance and Bearing on the Globe
#=============================================================================

# Mean radius of earth in meters
radius_of_earth = 6371000

# Compute distance (approximate) in meters from p1 to p2
# See: http://www.movable-type.co.uk/scripts/latlong.html
def points_distance_pythagorian(p1, p2):
	lat1 = math.radians(p1[0])
	lon1 = math.radians(p1[1])
	lat2 = math.radians(p2[0])
	lon2 = math.radians(p2[1])
	x = (lon2-lon1) * math.cos((lat1 + lat2)/2)		# longitudinal distance (figured at center of path)
	y = (lat2-lat1)									# latitudinal distance
	d = math.sqrt(x*x + y*y)						# Pythagerian theorem
	return d * radius_of_earth						# radians to kilometers

# Compute bearing in degress from north of p2 from p1
# See: http://www.movable-type.co.uk/scripts/latlong.html
def points_bearing(p1, p2):
	lat1 = math.radians(p1[0])
	lon1 = math.radians(p1[1])
	lat2 = math.radians(p2[0])
	lon2 = math.radians(p2[1])
	dLon = lon2 - lon1
	x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
	y = math.sin(dLon) * math.cos(lat2)
	bearing = math.atan2(y, x)
	return (math.degrees(bearing) + 360) % 360

#=============================================================================
# Test
#=============================================================================
if __name__ == "__main__":
	print "=== Polygon ==="

	coords = [(832,1093),(810,1121),(787,1156),(827,1173),(838,1167),(858,1157),(873,1132),(873,1107),(832,1093)]
	print "Coords:", coords
	poly = Polygon(coords)
	print "Centroid", poly.centroid()

	print "=== Bounding Box ==="
	bbox = BoundingBox()
	print "Empty:", str(bbox)
	bbox.add_point(Point(42, -72))
	bbox.add_point(Point(42.5, -73))
	print "Filled:", str(bbox)
	print "Center:", bbox.center()

	print "=== Two Points ==="
	for points in [
		[[45, -75], [45, -75]],		# same point
		[[45, -75], [45, -74]],		# one degree of longitude
		[[45, -75], [44, -75]],		# one degree of latitude
		[[45, -75], [44, -74]],		# one degree of each
		]:
		print "Points:", points
		print "Distance:", points_distance_pythagorian(*points)
		print "Bearing:", points_bearing(*points)
		print

	print dms_lat_lon(42.251, -72.251)

	print Points([[42.00, -72.00], [43.00, -73.00]])

