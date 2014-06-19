#=============================================================================
# gpx_layer_routes.py
# Map layer which shows the routes from a GPX file
# Copyright 2013, Trinity College
# Last modified: 15 August 2013
#=============================================================================

import gtk
import math

import pykarta.geometry
import pykarta.draw
from gpx_layer import GpxVectorLayer
from gpx_data_gpx import GpxRoute, GpxRoutePoint
import gpx_colors

class RouteLayer(GpxVectorLayer):
	def __init__(self, gpx_data):
		GpxVectorLayer.__init__(self)

		self.layer_objs = gpx_data.routes
		self.layer_objs.add_client("map_layer", self)

		self.radius = 5.0
		self.zoomed_route_i = None
		self.selected_path = None
		self.drag_obj_indexes = None
		self.dragged = False
		self.draw_obj_index = None
		self.draw_append = True

	def set_tool(self, tool):
		GpxVectorLayer.set_tool(self, tool)

		self.drag_obj_indexes = None
		self.draw_obj_index = None

		if tool == "tool_select":
			return _("Click to select route points.")
		elif tool == "tool_adjust":
			return _("Drag route points to desired position. Drag small dots to create intermediate points.")
		elif tool == "tool_draw":
			return _("Click on end of route to extend or in open area to start new route. Shift click last point.")
		elif tool == "tool_delete":
			return _("Click on route points to delete them.")
		else:
			return ""

	# Receive notification of changes in the selection which are made
	# by some other client of the data store.
	def on_select(self, path, source, client_name):
		self.selected_path = path

		# If something was selected in this layer and something other than
		# a picker was used to do it,
		if path != None and source != 'picker' and source != 'tools_route':

			# If clicked on whole route or a point in a route other than the
			# selected one, move the viewport to show the entire route.
			if len(path) == 1 or path[0] != self.zoomed_route_i:
				route_obj = self.layer_objs[path[0]]
				bbox = pykarta.geometry.BoundingBox()
				for point in route_obj:
					bbox.add_point(point)
				self.containing_map.zoom_to_extent(bbox)
				self.zoomed_route_i = path[0]
		
			# Click on a different point in the same route.
			# Most cases: Move the viewport, but do not change the zoom.
			# Double click on treeview: center and zoom in
			if len(path) == 2:
				point_obj = self.layer_objs[path[0]][path[1]]
				if source == 'treeview_double_click':
					self.containing_map.set_center_and_zoom_in(point_obj.lat, point_obj.lon, 16)
				else:
					self.containing_map.make_visible(point_obj.lat, point_obj.lon)
	
		self.containing_map.queue_draw()

	# Initiate a change in the selection.
	def select(self, path):
		self.selected_path = path
		self.layer_objs.select(self.selected_path, 'map_layer')

	# Called whenever the map viewport changes or the objects
	# in view in this layer change. This builds a list of objects
	# to be draw and their coordinates in pixel space.
	def do_viewport(self):
		map_bbox = self.containing_map.get_bbox()
		self.visible_objs = []
		route_i = 0
		for route in self.layer_objs:
			if route.gpxtp_show:
				if route.get_bbox().overlaps(map_bbox):		# if in (or a least near) viewport
					self.visible_objs.append(self.GpxRouteDrawn(route_i, route, self))
			route_i += 1
		self.containing_map.feedback.debug(1, " %d of %d routes are in view" % (len(self.visible_objs), len(self.layer_objs)))

	# Called whenever the map must be redrawn
	def do_draw(self, ctx):
		zoom = self.containing_map.get_zoom()
		# Step through those routes which are in view.
		for route_drawn in self.visible_objs:
			route_drawn.draw(ctx)

	# Called when any mouse button is pressed down
	def on_button_press(self, gdkevent):
		# If this layer is not active, we are done.
		if self.tool == None:
			return False

		# If not single click with left button, we are done.
		if gdkevent.type != gtk.gdk.BUTTON_PRESS or gdkevent.button != 1:
			return False

		# If the drawing of a route is already in progress, add a point.
		if self.tool == "tool_draw" and self.draw_obj_index is not None:
			route = self.layer_objs[self.draw_obj_index]
			point_i = len(route)
			lat, lon = self.containing_map.unproject_point(gdkevent.x, gdkevent.y)
			point = GpxRoutePoint(lat, lon)
			point.src = "User Placed"
			if self.draw_append:		# add to end
				route.append(point)
			else:						# add to beginning
				route.insert(0, point)
			self.select((self.draw_obj_index, point_i))	# select newly added point
			if gdkevent.state & gtk.gdk.SHIFT_MASK:		# If shift-click, this is the last point
				self.draw_obj_index = None				# turn off draw mode
			else:
				point.type = 'guide'
			return True

		# User may have clicked on an existing point. Step thru the points of each
		# visible route looking for one that is close to the place where
		# the user hit.
		route_drawn_i = len(self.visible_objs)
		for route_drawn in reversed(self.visible_objs):
			route_drawn_i -= 1		# interating in reverse

			# Step thru the (explicit) points.
			point_i = 0
			for point in route_drawn.explicit_pts:
				x, y = point
				if abs(gdkevent.x - x) <= self.radius and abs(gdkevent.y - y) <= self.radius:
					print "Hit route point: (%d,%d,%d)" % (route_drawn.index, route_drawn_i, point_i)
					if self.tool == "tool_delete":
						#del self.layer_objs[route_drawn.index][point_i]	# triggers do_viewport()
						#if len(self.layer_objs[route_drawn.index]) == 0:	# if route empty, delete
						#	del self.layer_objs[route_drawn.index]
						del route_drawn.route[point_i]	# triggers do_viewport()
						if len(route_drawn.route) == 0:	# if route empty, delete
							del self.layer_objs[route_drawn.index]
					elif self.tool == "tool_draw":
						self.draw_obj_index = route_drawn.index
						self.draw_append = (point_i > 0)
					elif self.tool != None:		# must be tool_select or tool_adjust
						self.select((route_drawn.index, point_i))
						if self.tool == 'tool_adjust':
							self.drag_obj_indexes = [route_drawn_i, point_i]
						self.containing_map.queue_draw()
					else:
						print "Route layer is not active."
					return True
				point_i += 1

			# Nope? Then see whether one of the phantom points was hit.
			for point in route_drawn.phantom_points:
				x, y, point_i = point
				if abs(gdkevent.x - x) <= self.radius and abs(gdkevent.y - y) <= self.radius:
					print "Hit phantom route point"

					# Create a new point at the mouse position
					lat, lon = self.containing_map.unproject_point(gdkevent.x, gdkevent.y)
					point = GpxRoutePoint(lat, lon)
					point.name = "Guide Point"
					point.type = "guide"
					point.src = "User Placed"

					print "New point comes after:", point_i
					route = self.layer_objs[route_drawn.index]
					route[point_i].route_shape = []
					route.insert(point_i+1, point)	# triggers do_viewport()

					self.drag_obj_indexes = [route_drawn_i, point_i+1]		# should come out like this
					self.select((route_drawn.index, point_i+1))
					return True

		# No point hit. User clicked in an open area. If the draw tool is
		# active, create a new route and put the first point at the place
		# where the user hit.
		if self.tool == "tool_draw":
			self.draw_obj_index = len(self.layer_objs)
			route = GpxRoute()
			route.name = "New Route"
			self.layer_objs.append(route)		# triggers do_viewport()
			lat, lon = self.containing_map.unproject_point(gdkevent.x, gdkevent.y)
			point = GpxRoutePoint(lat, lon)
			point.src = "User Placed"
			route.append(point)
			self.draw_append = True
			self.select((self.draw_obj_index, 0))
			return True

		# Let click fall through to next layer.
		return False

	# This is called when the mouse is moved over the map.
	def on_motion(self, gdkevent):
		if self.drag_obj_indexes:
			route_drawn_i, point_i = self.drag_obj_indexes
			self.visible_objs[route_drawn_i].drag(point_i, int(gdkevent.x), int(gdkevent.y))
			self.dragged = True
			return True
		return False

	# This is called when a mouse button is released over the map.
	def on_button_release(self, gdkevent):
		if self.drag_obj_indexes:								# is dragging in progress?
			route_drawn_i, point_i = self.drag_obj_indexes
			route_drawn = self.visible_objs[route_drawn_i]		# find this route in the drawing list
			if self.dragged:
				route_drawn.drop(point_i)						# set lat and lon
				self.dragged = False
			else:
				del route_drawn.route[point_i]
			self.layer_objs.touch((route_drawn.index, point_i))	# so treeview will be updated
			self.select(self.selected_path)						# so form will be updated
			self.drag_obj_indexes = None						# stop dragging
			return True
		return False

	# The class wraps up the information about how to draw a visible route in pixel space.
	class GpxRouteDrawn(object):
		def __init__(self, index, route, layer):
			self.index = index
			self.route = route
			self.layer = layer
			self.zoom = layer.containing_map.get_zoom()
	
			# Project the explicit points which the user placed
			self.explicit_pts = self.layer.containing_map.project_points(self.route)
	
			# Load the point symbol renderers for the explicit points
			self.sym_renderers = []
			for point in self.route:
				sym = self.layer.containing_map.symbols.get_symbol(point.sym, default=None)
				if sym:
					self.sym_renderers.append(sym.get_renderer(self.layer.containing_map))
				else:
					self.sym_renderers.append(None)

			self.update_intermediate_pts()

			self.color = gpx_colors.rgb_by_name.get(route.gpxx_DisplayColor, (0.0, 0.0, 1.0, 1.0))

		# Make a list of all points including the intermediate "shape points"
		# which may be contained in each explicit point.
		def update_intermediate_pts(self):

			self.shape_pts = []
			i = 0
			for point in self.route:
				self.shape_pts.append(self.explicit_pts[i])
				self.shape_pts.extend(self.layer.containing_map.project_points(point.route_shape))
				i += 1

			self.phantom_points = []
			i = 0
			while i < (len(self.explicit_pts) - 1):
				p1 = self.explicit_pts[i]	
				p2 = self.explicit_pts[i+1]
				xdistance = abs(p2[0] - p1[0])
				ydistance = abs(p2[1] - p1[1])
				distance = math.sqrt(xdistance * xdistance + ydistance * ydistance)
				if distance > 30:
					if len(self.route[i].route_shape) > 0:
						shape = self.route[i].route_shape
						point = shape[int(len(shape)/2)]
						x, y = self.layer.containing_map.project_point(point)
					else:
						x = (p1[0] + p2[0]) / 2
						y = (p1[1] + p2[1]) / 2
					self.phantom_points.append([x, y, i])
				i += 1

		# Actually draw the route
		def draw(self, ctx):

			# Create Cairo path for actual route line.
			pykarta.draw.route(ctx, self.shape_pts)

			# FIXME: use pykarta.draw.stroke_with_style()
			route_color = self.color
			ctx.set_source_rgba(*route_color)
			# The selected route is drawn thicker.
			if self.layer.selected_path and self.index == self.layer.selected_path[0]:
				ctx.set_line_width(3.0)
			else:
				ctx.set_line_width(1.5)
			ctx.stroke()

			# Route points can have symbols. Draw them.
			for i in range(len(self.explicit_pts)):
				x, y = self.explicit_pts[i]

				sym_renderer = self.sym_renderers[i]
				if sym_renderer:
					sym_renderer.blit(ctx, x, y)

				# If view is zoomed in far enough, and there is a label for this
				# point, draw it too.
				if self.zoom >= 13 and self.route[i].name:
					offset = self.layer.radius
					if sym_renderer:
						offset = max(offset, sym_renderer.label_offset)
					pykarta.draw.poi_label(ctx, x + offset, y, self.route[i].name)

			# If this layer is active, draw circles at the explicit route
			# points to indicate that they can be selected or dragged.
			if self.layer.tool is not None:
				point_i = 0
				style = {
					'stroke_color': route_color,
					'stroke_width': 1,
					}
				for point in self.explicit_pts:
					if (self.index, point_i) == self.layer.selected_path:
						x, y = point
						pykarta.draw.x_marks_the_spot(ctx, x, y, 10)	# FIXME: scale size

					if self.route[point_i].type == "guide":
						style['fill_color'] = (1.0, 1.0, 0.0, 1.0)	# yellow
					elif self.route[point_i].type == "stop":
						style['fill_color'] = (0.8, 0.2, 0.2, 1.0)	# red
					elif self.route[point_i].type == "maneuver":
						style['fill_color'] = (1.0, 0.65, 0.7, 1.0)	# pink
					else:
						style['fill_color'] = (1.0, 1.0, 1.0, 1.0)	# white

					pykarta.draw.node_dots(ctx, [point], style)

					point_i += 1

			# If points are draggable, add a plus between each pair of points
			# Dragging the plus will add a new point.
			if self.layer.tool == "tool_adjust":
				pykarta.draw.node_pluses(ctx, map(lambda i: i[:2], self.phantom_points), style={})

		# Call this to drag a point to another position. It updates only the
		# pixel-space coordinates. The latitude and longitude are updated
		# when drop() is called.
		def drag(self, point_index, x, y):
			self.explicit_pts[point_index] = [x, y]
			self.route[point_index].route_shape = []
			if point_index >= 1:
				self.route[point_index-1].route_shape = []
			self.update_intermediate_pts()
			self.layer.containing_map.queue_draw()

		# Call this when the user releases the dragged point. It updates
		# the latitude and the longitude.	
		def drop(self, point_index):
			x, y = self.explicit_pts[point_index]
			point = self.route[point_index]
			point.lat, point.lon = self.layer.containing_map.unproject_point(x, y)
			point.src = "User Placed"
			if point.type == "maneuver":	# If user moves an autoroute point, it should no
				point.type = ""				# longer be subject to deletion when route is stript.
			point.ele = ""					# not valid at new location
			point.time = ""					# no longer where we were then

