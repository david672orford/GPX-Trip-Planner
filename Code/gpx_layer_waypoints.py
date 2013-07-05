#=============================================================================
# gpx_layer_waypoints.py
# Waypoint map layer
# Copyright 2013, Trinity College
# Last modified: 1 May 2013
#=============================================================================

import gtk
import math
import cairo

from gpx_layer import GpxVectorLayer
from gpx_data_gpx import GpxWaypoint
import pykarta.draw

class WaypointLayer(GpxVectorLayer):

	def __init__(self, gpx_data):
		GpxVectorLayer.__init__(self)

		# Two-way connexion between data store and this layer
		self.layer_objs = gpx_data.waypoints
		self.layer_objs.add_client('map_layer', self)

		self.drag_wp = None			# member of visible_objs that is being dragged
		self.drag_slop = None

	def set_tool(self, tool):
		GpxVectorLayer.set_tool(self, tool)
		self.drag_wp = None

		if tool == "tool_select":
			return _("Click to select waypoints.")
		elif tool == "tool_adjust":
			return _("Drag waypoints to desired position.")
		elif tool == "tool_draw":
			return _("Click to add new waypoints.")
		elif tool == "tool_delete":
			return _("Click on waypoints to delete them.")
		else:
			return ""

	def on_select(self, path, source, client_name):
		self.selected_path = path
		if path != None:
			wp = self.layer_objs[path[0]]
			if source == 'treeview_double_click':
				self.containing_map.set_center_and_zoom_in(wp.lat, wp.lon, 14)
			else:	#if source != 'picker':
				self.containing_map.make_visible(wp.lat, wp.lon)
		self.containing_map.queue_draw()

	def do_viewport(self):
		self.visible_objs = []
		zoom = self.containing_map.get_zoom()
		waypoint_index = 0
		for waypoint in self.layer_objs:
			if waypoint.gpxtp_show:
				x, y = self.containing_map.project_point(waypoint)
				if x >= 0 and x < self.containing_map.width and y >= 0 and y < self.containing_map.height:	# if within viewport,
					waypoint_sym = self.containing_map.symbols.get_symbol(waypoint.sym, default="Dot").get_renderer(self.containing_map)
					self.visible_objs.append([
						waypoint_index,
						waypoint,
						waypoint_sym,
						x, y,
						waypoint.name if zoom >= 13 else None
						])
			waypoint_index += 1
		self.containing_map.feedback.debug(1, " %d of %d waypoints are in view" % (len(self.visible_objs), len(self.layer_objs)))

	def do_draw(self, ctx):
		selected_point = None
		for item in self.visible_objs:
			(waypoint_index, waypoint, waypoint_sym, x, y, waypoint_label) = item
			if self.selected_path and waypoint_index == self.selected_path[0]:
				pykarta.draw.x_marks_the_spot(ctx, x, y, waypoint_sym.x_size)
			waypoint_sym.blit(ctx, x, y)	# will not be None
			if waypoint_label:
				pykarta.draw.poi_label(ctx, x + waypoint_sym.label_offset, y, waypoint_label)

	def on_button_press(self, gdkevent):
		if self.tool == None:
			return False

		# If single click with left button,
		if gdkevent.type != gtk.gdk.BUTTON_PRESS or gdkevent.button != 1:
			return False

		# If we are drawing, create a new point at the click position.
		if self.tool == "tool_draw":
			lat, lon = self.containing_map.unproject_point(gdkevent.x, gdkevent.y)
			waypoint = GpxWaypoint(lat, lon)
			waypoint.name = "New Point"
			waypoint.src = "User Placed"
			waypoint_index = len(self.layer_objs)
			self.layer_objs.append(waypoint)
			self.selected_path = (waypoint_index,)
			self.layer_objs.select(self.selected_path, 'map_layer')
			return True

		# Compare the click coordinates to those of the visible Waypoints.
		# The first time we find a case where the click is within the bounding
		# box of a Waypoint image, we start to drag that Waypoint.
		i = 0
		for item in reversed(self.visible_objs):
			(waypoint_index, waypoint, waypoint_sym, waypoint_x, waypoint_y, waypoint_label) = item
			if waypoint_sym.hit((gdkevent.x - waypoint_x), (gdkevent.y - waypoint_y)):
				print "Hit Waypoint:", waypoint.name
				if self.tool == "tool_delete":
					del self.layer_objs[waypoint_index]
				else:
					self.selected_path = (waypoint_index,)
					self.layer_objs.select(self.selected_path, 'map_layer')
					if self.tool == "tool_adjust":
						self.drag_wp = item
						self.drag_slop = [(gdkevent.x - waypoint_x), (gdkevent.y - waypoint_y)]
					self.containing_map.queue_draw()
				return True
			i += 1
	
		return False

	def on_motion(self, gdkevent):
		if self.drag_wp:
			#print "(%d, %d)" % (gdkevent.x, gdkevent.y)
			self.drag_wp[3] = int(gdkevent.x - self.drag_slop[0])	# waypoint_x
			self.drag_wp[4] = int(gdkevent.y - self.drag_slop[1])	# waypoint_y
			self.containing_map.queue_draw()
			return True
		return False

	def on_button_release(self, gdkevent):
		if gdkevent.type != gtk.gdk.BUTTON_RELEASE or gdkevent.button != 1:
			return False
		if self.drag_wp is not None:
			(index, point, symbol, x, y, waypoint_name) = self.drag_wp
			print "Release at: (%d, %d)" % (x, y)
			point.lat, point.lon = self.containing_map.unproject_point(x, y)
			point.src = "User Placed"
			point.ele = ""		# not valid at new location
			point.time = ""		# no longer where we were then
			self.layer_objs.touch(index)
			self.layer_objs.select(self.selected_path, 'map_layer')		# so form will be updated
			self.drag_wp = None
			return True
		return False

