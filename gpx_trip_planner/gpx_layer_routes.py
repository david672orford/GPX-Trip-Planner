#=============================================================================
# gpx_layer_routes.py
# Copyright 2013--2023, Trinity College
# Last modified: 27 March 2023
#=============================================================================

from gi.repository import Gtk, Gdk
import math

import pykarta.geometry
import pykarta.draw
from gpx_layer import GpxEditableLayer, GpxTool, points_close
from gpx_data_gpx import GpxRoute, GpxRoutePoint
import gpx_colors

# This is a Pykarta map layer for rendering GPX routes
class RouteLayer(GpxEditableLayer):
	def __init__(self, gpx_data):
		GpxEditableLayer.__init__(self)

		self.layer_objs = gpx_data.routes
		self.layer_objs.add_client("map_layer", self)

		self.zoomed_route_i = None

		self.node_dot_diameter = 8.0

	# Receives notification of changes in the selection which are made
	# by some other client of the data store.
	def on_select(self, path, source, client_name):
		self.selected_path = path

		# If something was selected in this layer and something other than
		# a picker was used to do it,
		if path is not None and source != 'picker' and source != 'tools_route':

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
	
		self.redraw()

	# Wrap a route up in an object which contains its projected coordinates,
	# intermediate points, drawing routines, etc.
	def create_renderer(self, obj, index):
		class RouteRenderer(object):
			def __init__(self, obj, index, layer):
				self.route = obj
				self.index = index
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
	
				self.color = gpx_colors.rgb_by_name.get(self.route.gpxx_DisplayColor, (0.0, 0.0, 1.0, 1.0))
	
			# Make a list of all points including the intermediate "shape points"
			# which may be contained in each explicit point and the "phantom points"
			# which can be dragged to add new points.
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
			def draw(self, ctx, selected_path):
	
				# Create Cairo path for actual route line.
				pykarta.draw.route(ctx, self.shape_pts)
	
				# The selected route is drawn thicker.
				if selected_path and self.index == selected_path[0]:
					pykarta.draw.stroke_with_style(ctx, {'line-color':self.color,'line-width':3.0})
				else:
					pykarta.draw.stroke_with_style(ctx, {'line-color':self.color,'line-width':1.0})
	
				# Route points can have symbols. Draw them.
				for i in range(len(self.explicit_pts)):
					x, y = self.explicit_pts[i]
	
					sym_renderer = self.sym_renderers[i]
					if sym_renderer:
						sym_renderer.blit(ctx, x, y)
	
					# If view is zoomed in far enough, and there is a label for this
					# point, draw it too.
					if self.zoom >= 13 and self.route[i].name:
						offset = self.layer.node_dot_diameter / 2.0
						if sym_renderer:
							offset = max(offset, sym_renderer.label_offset)
						pykarta.draw.poi_label(ctx, x + offset, y, self.route[i].name)
	
				# If this layer is active, draw circles at the explicit route
				# points to indicate that they can be selected or dragged.
				if self.layer.drawing_tool is not None:
					point_i = 0
					style = {
						'stroke-color': self.color,
						'stroke-width': 1,
						'diameter': self.layer.node_dot_diameter,
						}
					for point in self.explicit_pts:
						# If this route point is selected, draw an X under it.
						if (self.index, point_i) == self.layer.selected_path:
							x, y = point
							pykarta.draw.x_marks_the_spot(ctx, x, y, 10)	# FIXME: scale size
	
						if self.route[point_i].type == "guide":
							style['fill-color'] = (1.0, 1.0, 0.0, 1.0)	# yellow
						elif self.route[point_i].type == "stop":
							style['fill-color'] = (0.8, 0.2, 0.2, 1.0)	# red
						elif self.route[point_i].type == "maneuver":
							style['fill-color'] = (1.0, 0.65, 0.7, 1.0)	# pink
						else:
							style['fill-color'] = (1.0, 1.0, 1.0, 1.0)	# white
	
						pykarta.draw.node_dots(ctx, [point], style)
	
						point_i += 1
	
				# If points are draggable, add a plus between each pair of points
				# Dragging the plus will add a new point.
				if selected_path and self.index == selected_path[0]:
					pykarta.draw.node_pluses(ctx, [i[:2] for i in self.phantom_points], style={})
	
			# Call this to drag a point to another position. It updates only the
			# pixel-space coordinates. The latitude and longitude are updated
			# when drop() is called.
			def drag(self, point_index, event_point):
				self.explicit_pts[point_index] = event_point

				# Remove surrounding route shape.
				self.route[point_index].route_shape = []
				if point_index >= 1:
					self.route[point_index-1].route_shape = []

				self.update_intermediate_pts()
				self.layer.redraw()
	
			# Call this when the user releases the dragged point. It updates
			# the latitude and the longitude.	
			def drop(self, point_index):
				x, y = self.explicit_pts[point_index]
				point = self.route[point_index]
				point.lat, point.lon = self.layer.containing_map.unproject_point(x, y)
				point.src = "User Placed"
				if point.type == "maneuver":	# If user moves an autoroute point, it should no
					point.type = "guide"		# longer be subject to deletion when route is stript.
				point.ele = ""					# not valid at new location
				point.time = ""					# no longer where we were then
				# FIXME: some kind of hack so that form will be updated
				self.layer.select(self.layer.selected_path)

		return RouteRenderer(obj, index, self)

	# Click to select a route. Bring mouse down on a point and move to drag it.
	def create_tool_select_adjust(self):
		class RouteSelector(GpxTool):
			def __init__(self, layer):
				self.layer = layer
				self.dragged_obj_i = None
				self.dragged = False

			def on_button_press(self, gdkevent):
				event_point = (gdkevent.x, gdkevent.y)
				route_drawn_i = len(self.layer.visible_objs)
				for route_drawn in reversed(self.layer.visible_objs):
					route_drawn_i -= 1		# interating in reverse
		
					# Step thru the (explicit) points.
					point_i = 0
					for point in route_drawn.explicit_pts:
						if points_close(point, event_point):
							path = (route_drawn.index, point_i)
							#print("Hit route point:", path)
							if path == self.layer.selected_path:
								self.dragged_obj_i = route_drawn_i
								self.layer.containing_map.set_cursor(Gdk.FLEUR)
							else:
								self.layer.select(path)
								self.layer.redraw()		# FIXME: really needed?
							return True
						point_i += 1

					# Nope? Then see whether one of the phantom points was hit.
					for point in route_drawn.phantom_points:
						x, y, point_i = point
						if points_close(point, event_point):
							print("Hit phantom route point")
		
							# Create a new point at the mouse position.
							lat, lon = self.layer.containing_map.unproject_point(*event_point)
							point = GpxRoutePoint(lat, lon)
							point.name = "Guide Point"
							point.type = "guide"
							point.src = "User Placed"
		
							print("New point comes after:", point_i)
							route = self.layer.layer_objs[route_drawn.index]
							route[point_i].route_shape = []
							route.insert(point_i+1, point)
							route_drawn.explicit_pts.insert(point_i+1, event_point)
		
							self.layer.select((route_drawn.index, point_i+1))	# select new point
							self.layer.containing_map.set_cursor(Gdk.FLEUR)
							self.dragged_obj_i = route_drawn_i
							return True

					# Nope? See if the whole thing was hit.
					points = route_drawn.explicit_pts
					i = 0
					limit = len(points) - 1
					while i < limit:
						if pykarta.geometry.plane_lineseg_distance(event_point, points[i], points[i+1]) < 10:
							self.layer.select((route_drawn.index,))
							return True
						i += 1

				return False

			def on_motion(self, gdkevent):
				if self.dragged_obj_i is not None:
					event_point = (gdkevent.x, gdkevent.y)
					self.layer.visible_objs[self.dragged_obj_i].drag(self.layer.selected_path[1], event_point)
					self.dragged = True
					return True
				return False

			def on_button_release(self, gdkevent):
				if self.dragged_obj_i is not None:					# is dragging in progress?
					# If cursor moved while mouse down, move point.
					if self.dragged:
						self.layer.visible_objs[self.dragged_obj_i].drop(self.layer.selected_path[1])
						self.dragged = False
					# No movement, delete point if not on end
					elif len(self.layer.visible_objs[self.dragged_obj_i].route) >= 3:
						route_i = self.layer.selected_path[0]
						del self.layer.visible_objs[self.dragged_obj_i].route[self.layer.selected_path[1]]
						self.layer.select((route_i,))				# reselect whole route
					self.dragged_obj_i = None						# stop dragging
					self.layer.containing_map.set_cursor(None)
					return True
				return False

		return RouteSelector(self)

	# First click starts a route. Each subsequent click adds the next point.
	# Shift click places the last point and closes the route.
	def create_tool_draw(self):
		class RouteDrawer(GpxTool):
			def __init__(self, layer):
				self.layer = layer
				self.obj_index = None		# position of new route in layer.layer_objs
				self.segement_start = None
				self.segment_end = None
			def on_button_press(self, gdkevent):
				# If no route is in progress, start one.
				if self.obj_index is None:
					route = GpxRoute()
					route.name = "New Route"
					self.obj_index = len(self.layer.layer_objs)
					self.layer.layer_objs.append(route)		# triggers do_viewport()
				else:
					route = self.layer.layer_objs[self.obj_index]
				# Create the new point.
				self.segment_start = self.segment_end = (gdkevent.x, gdkevent.y)
				lat, lon = self.layer.containing_map.unproject_point(gdkevent.x, gdkevent.y)
				point = GpxRoutePoint(lat, lon)
				point.src = "User Placed"
				# Add the new point to the route
				point_i = len(route)
				route.append(point)
				if gdkevent.get_state() & Gdk.ModifierType.SHIFT_MASK:		# Shift to place last point
					self.obj_index = None
				elif len(route) > 1:						# Points between first and last are guide points
					point.type = 'guide'
				return True
			def on_motion(self, gdkevent):
				if self.obj_index is not None:
					self.segment_end = (gdkevent.x, gdkevent.y)
					self.layer.redraw()
				return True
			def draw(self, ctx):
				if self.obj_index is not None:
					ctx.move_to(*self.segment_start)
					ctx.line_to(*self.segment_end)
					pykarta.draw.stroke_with_style(ctx, {"line-width":1,"line-dasharray":(3,2)})
		return RouteDrawer(self)

	# Click on a route to delete it entirely.
	def create_tool_delete(self):
		class RouteDeleter(GpxTool):
			def __init__(self, layer):
				self.layer = layer
			def on_button_press(self, gdkevent):
				event_point = (gdkevent.x, gdkevent.y)
				for route_drawn in reversed(self.layer.visible_objs):
					for point in route_drawn.explicit_pts:
						if points_close(point, event_point):
							print("Deleting route %d" % route_drawn.index)
							del self.layer.layer_objs[route_drawn.index]
							#self.layer.set_stale()
							return True
				return False
		return RouteDeleter(self)

