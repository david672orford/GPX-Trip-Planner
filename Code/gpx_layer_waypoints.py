#=============================================================================
# gpx_layer_waypoints.py
# Waypoint map layer
# Copyright 2013--2016, Trinity College
# Last modified: 31 March 2016
#=============================================================================

import gtk
import math
import cairo

from gpx_layer import GpxEditableLayer, GpxTool, points_close
from gpx_data_gpx import GpxWaypoint
import pykarta.draw

# This is a Pykarta map layer for rendering GPX waypoins
class WaypointLayer(GpxEditableLayer):

	def __init__(self, gpx_data):
		GpxEditableLayer.__init__(self)
		# Two way connexion between this layer and data store
		self.layer_objs = gpx_data.waypoints
		self.layer_objs.add_client('map_layer', self)

	# Receives notification of changes in the selection which are made
	# by some other client of the data store.
	def on_select(self, path, source, client_name):
		if path is not None:
			wp = self.layer_objs[path[0]]
			if source == 'treeview_double_click':
				self.containing_map.set_center_and_zoom_in(wp.lat, wp.lon, 14)
			else:
				self.containing_map.make_visible(wp.lat, wp.lon)
		GpxEditableLayer.on_select(self, path, source, client_name)

	# Wrap a waypoint up in an object which contains its projected
	# coordinates and marker image.
	def create_renderer(self, obj, index):
		class WaypointRenderer(object):
			def __init__(self, obj, index, layer):
				self.obj = obj
				self.index = index
				containing_map = layer.containing_map
				self.projected_point = containing_map.project_point(obj)
				self.sym = containing_map.symbols.get_symbol(obj.sym, default="Dot").get_renderer(containing_map)
				self.label = obj.name if containing_map.get_zoom() > 8 else None
			def draw(self, ctx, selected_path):
				x, y = self.projected_point
				if selected_path is not None and self.index == selected_path[0]:
					pykarta.draw.x_marks_the_spot(ctx, x, y, self.sym.x_size)
				self.sym.blit(ctx, x, y)
				if self.label:
					pykarta.draw.poi_label(ctx, x + self.sym.label_offset, y, self.label)
			def move(self, x, y):
				self.projected_point = (x, y)
			def drop(self, containing_map):
				obj = self.obj
				obj.lat, obj.lon = containing_map.unproject_point(*self.projected_point)
				obj.src = "User Placed"
				obj.ele = ""		# not valid at new location
				obj.time = ""		# no longer where we were then
		return WaypointRenderer(obj, index, self)

	# Click once to select a waypoint. Bring the mouse down again
	# and move to drag it to a new position.
	def create_tool_select_adjust(self):
		class WaypointSelector(GpxTool):
			def __init__(self, layer):
				self.layer = layer
				self.dragged_obj = None
				self.moved = False
			def on_button_press(self, gdkevent):
				event_point = (gdkevent.x, gdkevent.y)
				for obj in reversed(self.layer.visible_objs):
					if points_close(obj.projected_point, event_point):
						if self.layer.selected_path is not None and self.layer.selected_path[0] == obj.index:
							self.dragged_obj = obj
							self.layer.containing_map.set_cursor(gtk.gdk.FLEUR)
						else:
							self.layer.select((obj.index,))
						return True
				return False
			def on_motion(self, gdkevent):
				if self.dragged_obj is not None:
					self.dragged_obj.move(gdkevent.x, gdkevent.y)
					self.layer.redraw()
					self.moved = True
					return True
				return False
			def on_button_release(self, gdkevent):
				if self.dragged_obj is not None:
					if self.moved:
						self.dragged_obj.drop(self.layer.containing_map)
						self.layer.layer_objs.touch(self.dragged_obj.index)
						self.layer.select(self.layer.selected_path)		# so form will be updated
					self.layer.containing_map.set_cursor(None)
					self.layer.redraw()
					self.dragged_obj = None
					self.moved = False
					return True
				return False
		return WaypointSelector(self)

	# Click to create waypoints.
	def create_tool_draw(self):
		class WaypointDrawer(GpxTool):
			def __init__(self, layer):
				self.layer = layer
			def on_button_press(self, gdkevent):
				lat, lon = self.layer.containing_map.unproject_point(gdkevent.x, gdkevent.y)
				waypoint = GpxWaypoint(lat, lon)
				waypoint.name = "New Point"
				waypoint.src = "User Placed"
				waypoint_index = len(self.layer.layer_objs)
				self.layer.layer_objs.append(waypoint)
				self.layer.set_stale()
				self.layer.select((waypoint_index,))
				return True
		return WaypointDrawer(self)

	# Click to delete waypoints.
	def create_tool_delete(self):
		class WaypointDeleter(GpxTool):
			def __init__(self, layer):
				self.layer = layer
			def on_button_press(self, gdkevent):
				event_point = (gdkevent.x, gdkevent.y)
				for obj in reversed(self.layer.visible_objs):
					if points_close(obj.projected_point, event_point):
						del self.layer.layer_objs[obj.index]
						#self.layer.set_stale()
						return True
				return False
		return WaypointDeleter(self)

