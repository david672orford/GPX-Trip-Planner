#=============================================================================
# gpx_layer_photos.py
# Photos map layer
# Copyright 2013, 2014, Trinity College
# Last modified: 7 November 2013
#=============================================================================

import gtk

from pykarta.maps.layers import MapLayer
import pykarta.draw

class PhotoLayer(MapLayer):
	def __init__(self, photos):
		MapLayer.__init__(self)
		self.layer_objs = photos
		self.tool = None
		self.visible_objs = []
		self.selected_path = None
		self.layer_objs.add_client("map_layer", self)

	def set_tool(self, tool):
		if tool is not None and tool != "tool_select_adjust":
			raise NotImplementedError
		self.tool = tool
		self.redraw()
		return _("Photos are now clickable.")

	def on_select(self, path, source, client_name):
		self.selected_path = path
		if path != None:
			photo = self.layer_objs[path[0]]
			if source == 'treeview_double_click':
				self.containing_map.set_center_and_zoom_in(photo.lat, photo.lon, 14)
			else:
				self.containing_map.make_visible(photo.lat, photo.lon)
		self.redraw()

	def do_viewport(self):
		self.visible_objs = []
		bbox = self.containing_map.get_bbox()
		zoom = self.containing_map.get_zoom()
		sym = self.containing_map.symbols.get_symbol("Camera").get_renderer(self.containing_map)
		photo_index = 0
		for photo in self.layer_objs:
			x, y = self.containing_map.project_point(photo)
			if x >= 0 and x < self.containing_map.width and y >= 0 and y < self.containing_map.height:	# if within viewport,
				self.visible_objs.append((photo_index, photo, x, y, sym))
			photo_index += 1

	def do_draw(self, ctx):
		for photo_index, photo, x, y, sym in self.visible_objs:
			if self.selected_path and self.selected_path[0] == photo_index:
				pykarta.draw.x_marks_the_spot(ctx, x, y, sym.x_size)
			sym.blit(ctx, x, y)

	def on_button_press(self, gdkevent):
		if self.tool == None:
			return False

		# If single click with left button,
		if gdkevent.type != gtk.gdk.BUTTON_PRESS or gdkevent.button != 1:
			return False

		for photo_index, photo, x, y, sym in self.visible_objs:
			if sym.hit((gdkevent.x - x), (gdkevent.y - y)):
				print "Hit photo:", photo.name
				self.selected_path = (photo_index,)
				self.layer_objs.select(self.selected_path, 'map_layer')
				self.redraw()
				return True

		return False


