#=============================================================================
# gpx_layer_pois.py
# POIs map layer
# Copyright 2013, 2014, Trinity College
# Last modified: 25 August 2014
#
# This is a static layer which displays POI icons loaded from CSV files
# by gpx_data_poi.py.  This is used for displaying POIs downloaded from
# websites such as <http://www.poi-factory.com/>. 
#=============================================================================

import gtk

from pykarta.maps.layers import MapLayer
import pykarta.draw

class PoiLayer(MapLayer):
	def __init__(self, poi_db):
		MapLayer.__init__(self)
		self.poi_db = poi_db
		self.tool = None
		self.visible_objs = []
		self.selected_path = None

		self.poi_db.add_client("map_layer", self)

	def set_tool(self, tool):
		if tool is not None and tool != "tool_select":
			raise NotImplementedError
		self.tool = tool
		self.containing_map.queue_draw()
		return _("POIs are now clickable.")

	def category_checkbox_changed(self):
		#print "POI layer: category checkbox changed"
		self.set_stale()

	# Unneeded
	#def on_select(self, path, source, client_name):
	#	print "poi select:", path, source, client_name
	#	self.selected_path = path
	#	self.containing_map.queue_draw()

	def get_symbol_renderer(self, poi):
		symbol = self.poi_db.symbols.get_symbol(poi.sym)
		if not symbol:
			symbol = self.containing_map.symbols.get_symbol("Dot")
		return symbol.get_renderer(self.containing_map)

	def do_viewport(self):
		#print "POI layer: do_viewport()"
		self.visible_objs = []
		bbox = self.containing_map.get_bbox()
		zoom = self.containing_map.get_zoom()
		if zoom >= 10 or self.tool is not None:
			for poi in self.poi_db.in_bbox(bbox):
				#print poi.oid, poi.name
				x, y = self.containing_map.project_point(poi)
				self.visible_objs.append((poi, x, y, self.get_symbol_renderer(poi), poi.name if zoom >= 12 else None))

	def do_draw(self, ctx):
		#print "POI layer: do_draw()"
		for poi, x, y, symbol_renderer, label in self.visible_objs:
			if self.selected_path and self.selected_path[0] == poi.oid:
				pykarta.draw.x_marks_the_spot(ctx, x, y, symbol_renderer.x_size)
			symbol_renderer.blit(ctx, x, y)
			if label:
				pykarta.draw.poi_label(ctx, x + symbol_renderer.label_offset, y, label)

	def on_button_press(self, gdkevent):
		if self.tool is None:
			return False

		# If single click with left button,
		if gdkevent.type != gtk.gdk.BUTTON_PRESS or gdkevent.button != 1:
			return False

		for poi, x, y, symbol_renderer, label in self.visible_objs:
			if symbol_renderer.hit((gdkevent.x - x), (gdkevent.y - y)):
				print "Hit POI:", poi.name
				self.selected_path = (poi.oid,)
				self.poi_db.select(self.selected_path, 'map_layer')
				return True

		return False

