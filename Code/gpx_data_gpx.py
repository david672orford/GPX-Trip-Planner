# gpx_data_gpx.py
# Copyright 2013, Trinity College
# Last modified: 18 July 2013

import gtk
import gobject
import xml.sax
import xml.sax.saxutils
import math

import pykarta.geometry
from pykarta.maps.projection import project_to_tilespace

#=============================================================================
# GPX format support
#
# GPX 1.0 Specification:
# http://www.topografix.com/gpx_manual.asp
#
# GPX 1.1 Specification:
# http://www.topografix.com/gpx.asp				Website
# http://www.topografix.com/GPX/1/1/			Schema
#
# Garmin extensions:
# http://www8.garmin.com/xmlschemas/GpxExtensions/v3/GpxExtensionsv3.xsd
# http://www.garmindeveloper.com/web-device/garmin-mass-storage-mode-devices/
# http://www.cgtk.co.uk/navigation/gpx (converts Google route to GPX with GPXX)
#
# Be careful! This code is somewhat fragile due to the way it stores
# Python objects in gtk.ListStores and gtk.TreeStores. Watch out for
# the tree iters.
#=============================================================================

#=============================================================================
# Base types for types in a GPX file
#=============================================================================

# A GPX way, route, or track point
class GpxPoint(object):
	children =                ['ele', 'time', 'name', 'cmt', 'desc', 'src', 'link', 'sym', 'type']
	__slots__ = ['lat', 'lon', 'ele', 'time', 'name', 'cmt', 'desc', 'src', 'link', 'sym', 'type']
	def __init__(self, *args):
		for child_name in self.children:
			setattr(self, child_name, "")
		self.link = None

		if len(args) == 2:				# GpxPoint(lat, lon)
			self.lat, self.lon = args
		elif len(args) == 1:			# GpxPoint(template_point)
			source = args[0]
			self.lat = source.lat
			self.lon = source.lon
			for child_name in self.children:
				setattr(self, child_name, getattr(source, child_name))

			# for GpxRoutePoint
			if hasattr(source, "route_shape"):
				self.route_shape = source.route_shape
		else:
			raise TypeError

	# This is what allows old functions to consume these objects.
	def __getitem__(self, index):
		if index == 0:
			return self.lat
		elif index == 1:
			return self.lon
		else:
			raise IndexError

	def write(self, writer, point_type="wpt"):
		writer.startElementNL(point_type, {'lat': repr(self.lat), 'lon': repr(self.lon)})

		for i in self.children:
			value = getattr(self, i)
			if i == "link":				# FIXME: should be true if i is an object
				if value != None:
					value.write(writer)
			elif value != "":
				writer.characters(" ")
				writer.simpleTextElement(i, value)

		self.write_extensions(writer)
				
		writer.endElementNL(point_type)

	def write_extensions(self, writer):
		pass

# <author>
#  <name>John Smith</name>
#  <email id="john" domain="example.com"/>
#  <link href="http://jsmith.example.com">
#   <text>Personal Website</text>
#   <type>text/html</type>
#  </link>
# </author>
class GpxPerson(object):
	__slots__ = ['name', 'email', 'link']
	#children = ['name', 'email', 'link']
	compat_children = {"author":"name", "email":"email"}
	def __init__(self):
		self.name = None
		self.email = None
		self.link = None
	def write(self, writer, person_type="author"):
		writer.characters(" ")
		writer.startElementNL(person_type, {})
		if self.name != None:
			writer.characters("  ")
			writer.simpleTextElement('name', self.name)
		if self.email != None:
			self.email.write(writer)
		if self.link != None:
			self.link.write(writer)
		writer.characters(" ")
		writer.endElementNL(person_type)

# <copyright author="John Smith">
#  <year>2010</year>
#  <license>Public Domain</license>
# </copyright>
class GpxCopyright(object):
	__slots__ = ['author', 'year', 'license']
	children = ['year', 'license']
	def __init__(self, author):
		self.author = author
		self.year = None
		self.license = None
	def write(self, writer):
		writer.characters(" ")
		writer.startElementNL("copyright", {'author': self.author})
		if self.year != None:
			writer.characters("  ")
			writer.simpleTextElement('year', self.year)
		if self.license != None:
			writer.characters("  ")
			writer.simpleTextElement('license', self.license)
		writer.characters(" ")
		writer.endElementNL("copyright")

# <link href="http://www.example.com">
#  <name>Example Link</name>
#  <type>text/html</type>
# </link>
class GpxLink(object):
	__slots__ = ('href', 'text', 'type')
	children = ('text', 'type')
	# For GPX 1.0
	compat_children = {"url":"href", "urlname":"text"}
	def __init__(self, href):
		self.href = href
		self.text = None
		self.type = None
	def write(self, writer, link_tag="link"):
		writer.characters(" ")
		writer.startElementNL(link_tag, {'href': self.href})
		if self.text != None:
			writer.characters("  ")
			writer.simpleTextElement('text', self.text)
		if self.type != None:
			writer.characters("  ")
			writer.simpleTextElement('type', self.type)
		writer.characters(" ")
		writer.endElementNL(link_tag)

# <email id="john" domain="example.com"/>
class GpxEmail(object):
	__slots__ = ['id', 'domain']
	#children = []
	def __init__(self, id, domain):
		self.id = id
		self.domain = domain
	def write(self, writer, email_tag="email"):
		writer.characters("   ")
		writer.startElement(email_tag, {'id': self.id, 'domain': self.domain})
		writer.endElementNL(email_tag)

# Filler for extension containers
class GpxExtension(object):
	__slots__ = ['parent']
	def __init__(self, parent):
		self.parent = parent

# Filler for unsupported tags
class GpxUnsupported(object):
	pass

# GpxWaypoints, GpxRoutes, and GpxTracks objects are derived from
# this (either directly or thru GpxToplevelListofLists).
# It serves to both store the data and coordinate the 
# communication between the TreeView and the map widgets.
class GpxToplevelList(object):
	def __init__(self):

		# The clients of this data store
		self._clients = {}

		self._selected = None		# path of selected row
		self.changes = False		# are their unsaved changes?

		self.datastore.connect("row-changed", self.row_changed_cb)
		self.datastore.connect("row-deleted", self.row_deleted_cb)

	# Called on changes to the gtk.ListStore or gtk.TreeStore
	def row_changed_cb(self, treemodel, path, iter):

		# Container objects have a iter property which must be set.
		obj = self.datastore.get_value(iter, 0)
		if hasattr(obj, 'iter'):
			obj.iter = treemodel.get_iter(path)		# supplied iter is temporary

		# Map layer may want to move point.
		try:
			self._clients['map_layer'].set_stale()
		except KeyError:
			pass

		# The document has been modified.
		self.changes = True

	# The case of a deleted row is simpler.
	def row_deleted_cb(self, treemodel, path):
		self.select(None, "del()")
		try:
			self._clients['map_layer'].set_stale()
		except KeyError:
			pass
		self.changes = True

	# Add a client which wants to be informed of changes to the selection.
	def add_client(self, client_name, client_function):
		self._clients[client_name] = client_function

	# Remove all rows
	def clear(self):
		self.select(None, "clear()")
		self.datastore.clear()
		self.changes = False

	# Select a member object in the GUI.
	# Path should be None to cancel the selection.
	def select(self, path, source):
		#print "%s: %s selected %s" % (self.__class__.__name__, source, path)
		self._selected = path
		for client_name, client_obj in self._clients.items():
			if client_name != source:
				client_obj.on_select(path, source, client_name)

	# Call this if you change the Python object which is stored in the
	# first (and only) column of the row. We read and write the value
	# in order to trigger the row-changed signal.
	def touch(self, path):
		iter = self.datastore.get_iter(path)
		value = self.datastore.get_value(iter, 0)
		self.datastore.set_value(iter, 0, value)

	# Number of top-level items.
	def __len__(self):
		return len(self.datastore)

	# Iterate over the top level items
	def __iter__(self):
		for i in self.datastore:
			yield i[0]

	# Get an item at any level
	def __getitem__(self, path):
		return self.datastore[path][0]

	# Delete an item at any level
	def __delitem__(self, path):
		del self.datastore[path]

# Parent for GpxRoutes and GpxTracks (which use gtk.TreeStore rather than gtk.ListStore).
class GpxToplevelListofLists(GpxToplevelList):
	def append(self, child):
		child.datastore = self.datastore
		self.datastore.append(None, [child])
	def write(self, writer):
		for child in self:
			child.write(writer)

#=============================================================================
# Actual types in a GPX file
#=============================================================================

# GPX file metadata
class GpxMetadata(object):
	children = ['name', 'desc', 'author', 'copyright', 'link', 'time', 'keywords']
	# From GPX 1.0
	compat_children = ('name', 'desc', 'author', 'email', 'time', 'bounds')
	def __init__(self):
		for child_name in self.children:
			setattr(self, child_name, None)
		self.changes = False		# are their unsaved changes?
	# Navigate path to metadata item (which may be in a child object)
	# and return it.
	def get_item(self, path):
		obj = self
		for attr_name in path:
			obj = getattr(obj, attr_name)
			if obj == None:
				break
		return obj
	# Navigate path to metadata item and set it. Mark the metadata
	# as changed.
	def set_item(self, path, value):
		obj = self
		for attr_name in path[:-1]:
			child_obj = getattr(obj, attr_name)
			if child_obj == None:
				if attr_name == 'author':
					child_obj = GpxPerson()
				elif attr_name == 'copyright':
					child_obj = GpxCopyright()
				elif attr_name == 'link':
					child_obj = GpxLink(None)
				elif attr_name == 'email':
					child_obj = GpxEmail(None, None)
				else:
					raise Exception("Missing attribute: %s" % attr_name)
				setattr(obj, attr_name, child_obj)
			obj = child_obj

		setattr(obj, path[-1], value)
		self.changes = True

	def write(self, writer):
		writer.startElementNL("metadata")
		for child_name in self.children:
			value = getattr(self, child_name)
			if value == None:
				pass
			elif type(value) == unicode or type(value) == str:
				if value != "":
					writer.characters(" ")
					writer.simpleTextElement(child_name, value)
			else:	# compound object
				value.write(writer)
		writer.endElementNL("metadata")

# List of waypoints
class GpxWaypoints(GpxToplevelList):
	def __init__(self):
		self.datastore = gtk.ListStore(gobject.TYPE_PYOBJECT)
		GpxToplevelList.__init__(self)
	def append(self, item):
		self.datastore.append([item])
	def write(self, writer):
		for poi in self:
			poi.write(writer, "wpt")

class GpxWaypoint(GpxPoint):
	def __init__(self, *args):
		GpxPoint.__init__(self, *args)
		self.gpxtp_show = True
	def write_extensions(self, writer):
		if not self.gpxtp_show:
			writer.startElementNL("extensions", {})
			writer.simpleTextElement("gpxtp:show", "false")
			writer.endElementNL("extensions")

class GpxGeocache(object):
	pass

# List of routes in GPX file
class GpxRoutes(GpxToplevelListofLists):
	def __init__(self):
		self.datastore = gtk.TreeStore(gobject.TYPE_PYOBJECT)
		self.picklist = gtk.ListStore(gobject.TYPE_STRING)
		self.picklist.append(["New Route"])
		GpxToplevelList.__init__(self)

	# The methods below hook the cooresponding methods in the superclass
	# in order to peek and keep self.picklist up-to-date.

	def append(self, child):
		GpxToplevelListofLists.append(self, child)
		self.picklist.append([child.name])

	def touch(self, path):
		GpxToplevelListofLists.touch(self, path)
		self.picklist[path[0]+1] = [self[path[0]].name]
		self[path[0]].bbox = None

	def clear(self):
		GpxToplevelListofLists.clear(self)
		save_first = self.picklist[0][0]
		self.picklist.clear()
		self.picklist.append([save_first])

	def __delitem__(self, path):
		print "delitem:", path
		GpxToplevelListofLists.__delitem__(self, path)
		if type(path) == int:
			path = (path,)
		if len(path) == 1:		# if whole route deleted,
			del self.picklist[path[0]+1]

# A single route (which contains of GpxRoutePoint objects)
class GpxRoute(object):
	children = ['name', 'cmt', 'desc', 'src', 'link', 'number', 'type']
	def __init__(self):
		self.datastore = None		# set by parent (GpxRoutes)
		self.iter = None			# set by parent
		for child_name in self.children:
			setattr(self, child_name, "")
		self.bbox = None
		self.gpxtp_show = True
		self.gpxx_DisplayColor = ""
	def __iter__(self):
		iter = self.datastore.iter_children(self.iter)
		while iter is not None:
			yield self.datastore.get_value(iter, 0)
			iter = self.datastore.iter_next(iter)
	def __getitem__(self, index):
		iter = self.datastore.iter_nth_child(self.iter, index)
		return self.datastore.get_value(iter, 0)
	def __len__(self):
		return self.datastore.iter_n_children(self.iter)
	def append(self, point):
		self.datastore.append(self.iter, [point])
		self.bbox = None
	def __delitem__(self, index):
		iter = self.datastore.iter_nth_child(self.iter, index)
		self.datastore.remove(iter)
		self.bbox = None
	def insert(self, index, item):
		iter = self.datastore.iter_nth_child(self.iter, index)
		self.datastore.insert_before(self.iter, iter, [item])
		self.bbox = None
	def write(self, writer):
		writer.startElementNL("rte")
		for i in self.children:
			value = getattr(self, i)
			if value != "":
				writer.simpleTextElement(i, value)
		if self.gpxx_DisplayColor != "" or not self.gpxtp_show:
			writer.startElementNL("extensions", {})
			if self.gpxx_DisplayColor != "":
				writer.startElementNL("gpxx:RouteExtension", {})
				writer.simpleTextElement("gpxx:DisplayColor", self.gpxx_DisplayColor)
				writer.endElementNL("gpxx:RouteExtension")
			if not self.gpxtp_show:
				writer.simpleTextElement("gpxtp:show", "false")
			writer.endElementNL("extensions")
		for point in self:
			point.write(writer, "rtept")
		writer.endElementNL("rte")
	def get_bbox(self):
		if self.bbox == None:
			self.bbox = pykarta.geometry.BoundingBox()
			for point in self:
				self.bbox.add_point(point)
		return self.bbox

class GpxRoutePoint(GpxPoint):
	__slots__ = ['route_shape']
	def __init__(self, *args):
		GpxPoint.__init__(self, *args)
		self.route_shape = []
	def write_extensions(self, writer):
		if len(self.route_shape) > 0:
			writer.startElementNL("extensions", {})
			writer.startElementNL("gpxx:RoutePointExtension", {})
			for point in self.route_shape:
				writer.startElement("gpxx:rpt", {'lat': repr(point.lat), 'lon': repr(point.lon)})
				writer.endElementNL("gpxx:rpt")
			writer.endElementNL("gpxx:RoutePointExtension")
			writer.endElementNL("extensions")

# For GpxRoutePoint.route_shape
class GpxRouteShapePoint(object):
	__slots__ = ['lat', 'lon']
	def __init__(self, lat, lon):
		self.lat = lat
		self.lon = lon

class GpxTracks(GpxToplevelListofLists):
	def __init__(self):
		self.datastore = gtk.TreeStore(gobject.TYPE_PYOBJECT)
		GpxToplevelList.__init__(self)

	# Split a track segment
	# FIXME: bounding box should be invalidated
	def split(self, path):
		if len(path) == 3:		# point selected

			# Save the data from the rows to be split off
			points = []
			remove_paths = []
			iter = self.datastore.get_iter(path)
			while iter != None:
				points.append(self.datastore.get_value(iter, 0))
				remove_paths.insert(0, self.datastore.get_path(iter))
				iter = self.datastore.iter_next(iter)
			print "points:", points

			# Remove the rows to be split off
			for remove_path in remove_paths:
				iter = self.datastore.get_iter(remove_path)
				self.datastore.remove(iter)

			# Create a new track segment
			iter_track = self.datastore.get_iter(path[0])
			iter_segment = self.datastore.get_iter(path[:2])
			new_seg = GpxTrackSegment()
			new_seg.datastore = self.datastore
			self.datastore.insert_after(iter_track, iter_segment, [new_seg])

			# Put the removed points into the new track segment
			for point in points:
				new_seg.append(point)

	# These are for recording live GPS tracks
	def new_segment(self, track_name):
		track = None
		for child in self:
			if child.name == track_name:
				track = child
				break
		if track is None:
			track = GpxTrack()
			track.name = track_name
			self.append(track)
		segment = GpxTrackSegment()
		track.append(segment)
		return segment

# A GPX track
class GpxTrack(object):
	children = ['name', 'cmt', 'desc', 'src', 'link', 'number', 'type']
	def __init__(self):
		self.datastore = None		# set by parent (GpsTracks)
		self.iter = None			# set by parent
		for child_name in self.children:
			setattr(self, child_name, "")
		self.gpxtp_show = True
		self.gpxx_DisplayColor = ""
	def __iter__(self):
		iter = self.datastore.iter_children(self.iter)
		while iter != None:
			trackseg = self.datastore.get_value(iter, 0)
			yield trackseg
			iter = self.datastore.iter_next(iter)
	def __getitem__(self, index):
		iter = self.datastore.iter_nth_child(self.iter, index)
		return self.datastore.get_value(iter, 0)
	def append(self, segment):
		segment.datastore = self.datastore
		self.datastore.append(self.iter, [segment])
	def write(self, writer):
		writer.startElementNL("trk")
		for i in self.children:
			value = getattr(self, i)
			if value != "":
				writer.simpleTextElement(i, value)
		if self.gpxx_DisplayColor != "" or not self.gpxtp_show:
			writer.startElementNL("extensions", {})
			if self.gpxx_DisplayColor != "":
				writer.startElementNL("gpxx:TrackExtension", {})
				writer.simpleTextElement("gpxx:DisplayColor", self.gpxx_DisplayColor)
				writer.endElementNL("gpxx:TrackExtension")
			if self.gpxtp_show:
				writer.simpleTextElement("gpxtp:show", "false")
			writer.endElementNL("extensions")
		for trackseg in self:
			trackseg.write(writer)
		writer.endElementNL("trk")

# A GPX track consists of one or more of these.
# Unlike GpxTrack, these can't have attributes.
class GpxTrackSegment(object):
	def __init__(self):
		self.datastore = None	# set by parent (GpxTrack)
		self.iter = None		# set by parent
		self.bbox = None
		self.projected_points = None
		self.projected_simplified_points = None
	def __iter__(self):
		iter = self.datastore.iter_children(self.iter)
		while iter != None:
			yield self.datastore.get_value(iter, 0)
			iter = self.datastore.iter_next(iter)
	def append(self, point):
		self.datastore.append(self.iter, [point])
		self.bbox = None
		self.projected_points = None
	def append_fix(self, fix):
		point = GpxPoint(fix.lat, fix.lon)
		# FIXME: record other attributes
		self.append(point)
	def __len__(self):
		return self.datastore.iter_n_children(self.iter)
	def __getitem__(self, index):
		iter = self.datastore.iter_nth_child(self.iter, index)
		return self.datastore.get_value(iter, 0)
	def __getattr__(self, attr):
		if attr == "name":
			return "Segment"
		else:
			raise AttributeError
	def write(self, writer):
		writer.startElementNL("trkseg")
		for point in self:
			point.write(writer, "trkpt")
		writer.endElementNL("trkseg")
	def get_bbox(self):
		if self.bbox == None:
			self.bbox = pykarta.geometry.BoundingBox()
			for point in self:
				self.bbox.add_point(point)
		return self.bbox
	# Return points projected to tilespace. The answer is cached.
	def get_projected_simplified_points(self, zoom):
		zoom = int(zoom + 0.5)
		if self.projected_points is None:
			self.projected_points = map(lambda p: project_to_tilespace(p.lat, p.lon, 0), self)
			self.projected_simplified_points = {}
		if not zoom in self.projected_simplified_points:
			tolerance = 1 / (256.0 * math.pow(2, zoom))
			self.projected_simplified_points[zoom] = pykarta.geometry.line_simplify(self.projected_points, tolerance)
			print "Simplified %d points to %d points at zoom level %d with tolerance %f" % (len(self.projected_points), len(self.projected_simplified_points[zoom]), zoom, tolerance)
		return self.projected_simplified_points[zoom]

#=============================================================================
# This object holds the data from one or more GPX files.
#=============================================================================

class GpxParseError(Exception):
	pass

class GpxData(xml.sax.handler.ContentHandler):
	def __init__(self):
		self.metadata = None
		self.waypoints = GpxWaypoints()
		self.routes = GpxRoutes()
		self.tracks = GpxTracks()
		self.debug = False

	# Has the GPX file been modified?
	def get_changes(self):
		return (self.metadata and self.metadata.changes) or self.waypoints.changes or self.routes.changes or self.tracks.changes

	# Clear the change indicators.
	def clear_changes(self):
		if self.metadata:
			self.metadata.changes = False
		self.waypoints.changes = False
		self.routes.changes = False
		self.tracks.changes = False

	# Throw away the data leaving the GPX file in memory empty.
	def clear(self):
		self.waypoints.clear()
		self.routes.clear()
		self.tracks.clear()

	# Returns an object which can be passed to get_bbox() after loading
	# more data in order to obtain the bounding box of only the new data.
	def get_mark(self):
		return (len(self.waypoints), len(self.routes), len(self.tracks))

	# Return the bounding box of all of the waypoints, routes, tracks.
	def get_bbox(self, mark=(0, 0, 0)):
		bbox = pykarta.geometry.BoundingBox()
		for point in list(self.waypoints)[mark[0]:]:
			bbox.add_point(point)
		for route in list(self.routes)[mark[1]:]:
			for point in route:
				bbox.add_point(point)
		for track in list(self.tracks)[mark[2]:]:
			for trackseg in track:
				for point in trackseg:
					bbox.add_point(point)
		return bbox

	# Write the data out using an GpxWriter() instance
	def write(self, writer):
		if self.metadata != None:
			self.metadata.write(writer)
		self.waypoints.write(writer)
		self.routes.write(writer)
		self.tracks.write(writer)

	# Load a GPX file
	def load_gpx(self, fh):
		# Used during parsing
		self.gpx_version = None
		self.tag_stack = []		# list of enclosing tags with innermost first
		self.obj_stack = []		# list of objects cooresponding to tags
		self.unsupported_count = 0

		self.parser = xml.sax.make_parser()
		self.parser.setContentHandler(self)
		self.parser.parse(fh)
		#self.changes = True		# probably not necessary

		print "%d unsupported tags" % self.unsupported_count

	# Callback from XML parser
	def startElement(self, name, attrs):
		if self.debug:
			print "<%s>" % name
			print " Tag stack:", self.tag_stack
			print " Obj stack:", self.obj_stack

		# Create an object to represent this tag and push it onto the start of obj_stack[].
		if len(self.tag_stack) == 0:
			if name == 'gpx':
				self.gpx_version = attrs.get('version')
				self.obj_stack.insert(0, self)
			
		elif self.tag_stack[0] == 'gpx':
			if name == 'wpt':
				new_point = GpxWaypoint(float(attrs.get('lat')), float(attrs.get('lon')))
				self.waypoints.append(new_point)
				self.obj_stack.insert(0, new_point)
			elif name == 'rte':
				new_route = GpxRoute()
				self.routes.append(new_route)
				self.obj_stack.insert(0, new_route)
			elif name == 'trk':
				new_track = GpxTrack()
				self.tracks.append(new_track)
				self.obj_stack.insert(0, new_track)
			elif name == "metadata" and self.gpx_version == "1.1":
				new_metadata = GpxMetadata()
				if self.metadata == None:			# if first one,
					self.metadata = new_metadata
				self.obj_stack.insert(0, new_metadata)
			elif self.gpx_version == "1.0" and name in GpxMetadata.compat_children:
				if name == "bounds":
					self.obj_stack.insert(0, None)		# ignore <bounds>
				else:
					self.obj_stack.insert(0, u"")
			else:
				print "Unsupported toplevel element:", name
				self.unsupported_count += 1
				self.obj_stack.insert(0, GpxUnsupported())

		elif self.tag_stack[0] == 'wpt':
			if name == "groundspeak:cache":
				new_geocache = GpxGeocache()
				self.obj_stack.insert(0, new_geocache)
			else:
				self.startElement_common(name, attrs)		# will push to obj_stack[]

		elif self.tag_stack[0] == 'rte':
			if name == 'rtept':
				new_point = GpxRoutePoint(float(attrs.get('lat')), float(attrs.get('lon')))
				self.obj_stack[0].append(new_point)		# add point to route
				self.obj_stack.insert(0, new_point)		# put point on top
			else:
				self.startElement_common(name, attrs)

		elif self.tag_stack[0] == 'rtept':
			self.startElement_common(name, attrs)

		elif self.tag_stack[0] == 'trk':
			if name == 'trkseg':
				new_trkseg = GpxTrackSegment()
				self.obj_stack[0].append(new_trkseg)	# add segment to track
				self.obj_stack.insert(0, new_trkseg)	# put segment on top
			else:
				self.startElement_common(name, attrs)
				
		elif self.tag_stack[0] == 'trkseg':
			if name == 'trkpt':
				new_point = GpxPoint(float(attrs.get('lat')), float(attrs.get('lon')))
				self.obj_stack[0].append(new_point)		# add point to track segment
				self.obj_stack.insert(0, new_point)		# put point on top
			else:
				raise GpxParseError

		elif self.tag_stack[0] == 'trkpt':
			self.startElement_common(name, attrs)

		elif self.tag_stack[0] == 'metadata':
			if name == 'author':
				author = GpxPerson()
				self.metadata.author = author
				self.obj_stack.insert(0, author)
			elif name == 'copyright':
				copyright = GpxCopyright(attrs['author'])
				self.metadata.copyright = copyright
				self.obj_stack.insert(0, copyright)
			elif name == 'bounds':
				self.obj_stack.insert(0, None)		# ignore
			else:
				self.startElement_common(name, attrs)

		# <author>
		#  <name>John Smith</name>
		#  <email id="jsmith" domain="example.com"/>
		#  <link href="http://jsmith.example.com">
		#   <text>John Smith's website</text>
		#   <type></type>
		#  </link>
		# </author>
		elif self.tag_stack[0] == 'author':
			if name == 'name':
				self.obj_stack.insert(0, u"")
			elif name == 'email':
				email = GpxEmail(attrs['id'], attrs['domain'])
				self.obj_stack[0].email = email
				self.obj_stack.insert(0, email)
			elif name == 'link':
				link = GpxLink(attrs['href'])
				self.obj_stack[0].link = link
				self.obj_stack.insert(0, link)
			else:
				raise GpxParseError

		# The children of <copyright> and <link> contain only text.
		elif self.tag_stack[0] == 'copyright' or self.tag_stack[0] == 'link':
			if name in self.obj_stack[0].children:
				self.obj_stack.insert(0, u"")
			else:
				raise GpxParseError

		elif self.tag_stack[0] == 'extensions':
			if name == "gpxtp:show":
				self.obj_stack.insert(0, u"")
			elif name.startswith('gpxx:'):
				self.obj_stack.insert(0, GpxExtension(self.obj_stack[0]))
			else:
				print "Unsupported extension:", self.tag_stack, name
				self.unsupported_count += 1
				self.obj_stack.insert(0, GpxUnsupported())
				
		elif self.tag_stack[0] == 'gpxx:RouteExtension':
			if name == "gpxx:DisplayColor":
				self.obj_stack.insert(0, u"")
			else:
				print "Unsupported extension:", self.tag_stack, name
				self.unsupported_count += 1
				self.obj_stack.insert(0, GpxUnsupported())

		elif self.tag_stack[0] == 'gpxx:RoutePointExtension':
			if name == "gpxx:rpt":
				point = GpxRouteShapePoint(float(attrs.get('lat')), float(attrs.get('lon')))
				self.obj_stack[2].route_shape.append(point)	# thru two levels of extension tags
				self.obj_stack.insert(0, None)	# dummy
			else:
				print "Unsupported extension:", self.tag_stack, name
				self.unsupported_count += 1
				self.obj_stack.insert(0, GpxUnsupported())

		elif self.tag_stack[0] == 'gpxx:TrackExtension':
			if name == "gpxx:DisplayColor":
				self.obj_stack.insert(0, u"")
			else:
				print "Unsupported extension:", self.tag_stack, name
				self.unsupported_count += 1
				self.obj_stack.insert(0, GpxUnsupported())

		elif self.tag_stack[0].startswith('groundspeak:'):
			self.obj_stack.insert(0, GpxUnsupported())	# FIXME: add support

		else:
			print "Unsupported element:", self.tag_stack, name
			self.unsupported_count += 1
			self.obj_stack.insert(0, GpxUnsupported())

		# Now that the object is in place, push to tag onto the tag stack
		# as the innermost (index 0) element.
		self.tag_stack.insert(0, name)

		# Make sure one and only one object was pushed to represent this tag.
		assert len(self.obj_stack) == len(self.tag_stack)

	# This is shared by <metadata>, <wpt>, <rte>, <rtept>, <trk>, <trkpt>.
	def startElement_common(self, name, attrs):
		if name in self.obj_stack[0].children:		# if element has such a child,
			if name == 'link':
				link = GpxLink(attrs['href'])
				self.obj_stack[0].link = link
				self.obj_stack.insert(0, link)
			else:
				self.obj_stack.insert(0, u"")

		elif name == 'extensions':
			self.obj_stack.insert(0, GpxExtension(self.obj_stack[0]))

		elif self.gpx_version == "1.0" and name in GpxLink.compat_children and "link" in self.obj_stack[0].children:
			self.obj_stack.insert(0, u"")

		else:
			print "Unsupported element:", self.tag_stack, name
			self.unsupported_count += 1
			self.obj_stack.insert(0, GpxUnsupported())

	# Callback from XML parser for end tags
	def endElement(self, name):
		if self.debug:
			print "</%s>" % name
			print " Tag stack:", self.tag_stack
			print " Obj stack:", self.obj_stack

		# Pop the tag off the stack and make sure it is the one we were expecting.
		if len(self.tag_stack) < 1 or self.tag_stack.pop(0) != name:
			raise GpxParseError

		# Pop the cooresponding, newly constructed object off of the stack
		obj = self.obj_stack.pop(0)

		# Strings need to be inserted into their parent objects.
		if type(obj) is unicode:
			parent = self.obj_stack[0]

			while type(parent) is GpxExtension:		# step thru
				parent = parent.parent

			if name == 'gpxtp:show':
				value = (obj == 'true')
			else:
				value = obj

			if self.gpx_version == "1.0":
				if self.tag_stack[0] == "gpx" and name in GpxMetadata.compat_children:
					if parent.metadata is None:
						parent.metadata = GpxMetadata()
					parent = parent.metadata
				if name in GpxLink.compat_children and hasattr(parent, 'link'):
					if parent.link is None:
						parent.link = GpxLink(None)
					parent = parent.link
					name = GpxLink.compat_children[name]
				elif name in GpxPerson.compat_children:
					if parent.author is None:
						parent.author = GpxPerson()
					name = GpxPerson.compat_children[name]

			setattr(parent, name.replace(':','_'), value)

		elif type(obj) is str:
			raise AssertionError

		# FIXME: figure out why this is necessary
		if name == 'rte':
			self.routes.touch((len(self.routes)-1,))

		assert len(self.obj_stack) == len(self.tag_stack)

	# Callback from XML parser
	def characters(self, text):
		if self.debug:
			print "Characters:", text
		if len(self.obj_stack) > 0 and type(self.obj_stack[0]) is unicode:
			self.obj_stack[0] += text

#=============================================================================
# To create a GPX file from data stored in the above objects, create one
# of these and pass it to the write() method of an object.
#=============================================================================
class GpxWriter(xml.sax.saxutils.XMLGenerator):

	def __init__(self, fh):
		fh.write("<?xml version='1.0' encoding='UTF-8'?>\n")
		xml.sax.saxutils.XMLGenerator.__init__(self, fh)
		self.startElementNL("gpx", {
			'version': "1.1",
			'creator': "GPX Trip Planner",
			'xmlns': "http://www.topografix.com/GPX/1/1",
			'xmlns:gpxx': "http://www.garmin.com/xmlschemas/GpxExtensions/v3",
			'xmlns:gpxrp': "http://www.trincoll.edu/xmlschemas/gpx-route-planner/v1",
			})

	def __del__(self):
		self.endElementNL("gpx")

	def startElementNL(self, tag, attrs={}):
		self.startElement(tag, attrs)
		self.characters("\n")

	def endElementNL(self, tag):
		self.endElement(tag)
		self.characters("\n")

	def simpleTextElement(self, tag, text):
		self.startElement(tag, {})
		self.characters(text)
		self.endElementNL(tag)


