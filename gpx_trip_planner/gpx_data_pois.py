# Copyright 2013--2025 Trinity College

import os
from gi.repository import Gtk
from gi.repository import GObject
import sqlite3
import glob

from gpx_data_gpx import GpxPoint
from pykarta.maps.symbols import MapSymbolSet

#==============================================================
# The POI categories formatted as a list acceptable to
# GpxFancyTreeview()
#==============================================================
class PoiCategories(object):
	def __init__(self, poi_db):
		self.poi_db = poi_db
		self.datastore = Gtk.ListStore(GObject.TYPE_PYOBJECT)
		self.visible_set = set()
	# Add a POI category
	def add(self, name):
		self.datastore.append([PoiCategory(name)])
		#self.visible_set.add(name)
	# We don't track the selection, so both of these are noops.
	def add_client(self, client_name, client_obj):
		pass
	def select(self, path, source):
		pass
	# This is needed so that that GpxFancyTreeview() can change visibility.
	def __getitem__(self, path):
		return self.datastore[path][0]
	# GpxFancyTreeview() calls this after changing visibility.
	def touch(self, path):
		iter = self.datastore.get_iter(path)
		value = self.datastore.get_value(iter, 0)
		self.datastore.set_value(iter, 0, value)

		if value.gpxtp_show:
			self.visible_set.add(value.name)
		else:
			self.visible_set.remove(value.name)

		self.poi_db.category_checkbox_changed()

# This is enough like a GPX object to make GpxFancyTreeview() happy.
class PoiCategory(object):
	def __init__(self, name):
		self.gpxtp_show = False
		self.name = name
		self.desc = ""

#==============================================================
# Interface to the Sqlite database of POIs
# This display layer connects to this.
#==============================================================
class PoiDB(object):
	def __init__(self, filename):
		self.categories = PoiCategories(self)
		self._clients = {}
		self.conn = None
		self.cursor = None

		if os.path.exists(filename):
			print("Loading POI categories:")
			self.conn = sqlite3.connect(filename)
			self.cursor = self.conn.cursor()

			self.cursor.execute("SELECT DISTINCT symbol from pois")
			for row in self.cursor:
				print("  %s" % row[0])
				self.categories.add(row[0])

		print("Loading POI symbols...")
		self.symbols = MapSymbolSet()
		for filename in glob.glob("POIs/*.bmp"):
			print("  %s" % filename)
			self.symbols.add_raster_symbol(filename)

	def add_client(self, client_name, client_obj):
		self._clients[client_name] = client_obj
	def select(self, path, source):
		for client_name, client_obj in list(self._clients.items()):
			if client_name != source:
				client_obj.on_select(path, source, client_name)
	def category_checkbox_changed(self):
		self._clients['map_layer'].category_checkbox_changed()
	def in_bbox(self, bbox):
		if self.cursor:
			self.cursor.execute(
				"SELECT oid, name, description, symbol, latitude, longitude from pois where latitude >= ? and latitude <= ? and longitude >= ? and longitude <= ?",
				(bbox.min_lat, bbox.max_lat, bbox.min_lon, bbox.max_lon)
				)
			for row in self.cursor:
				if row[3] in self.categories.visible_set:		# symbol
					yield GpxPOI(row)
	def __getitem__(self, path):
		if self.cursor is None:
			raise AssertionError
		self.cursor.execute("SELECT oid, name, description, symbol, latitude, longitude from pois where oid = ?", (path[0],))
		row = self.cursor.fetchone()
		return GpxPOI(row)

class GpxPOI(GpxPoint):
	"""Representation of a single POI which we pass to the display layer"""
	def __init__(self, row):
		oid, name, description, symbol, lat, lon = row
		self.oid = oid
		GpxPoint.__init__(self, lat, lon)
		self.name = name
		self.desc = description
		self.sym = symbol
