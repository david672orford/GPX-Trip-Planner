# pykarta/maps/layers/vector.py
# An editable vector layer
# Copyright 2013, Trinity College
# Last modified: 28 February 2013

import math
import gtk

from pykarta.maps.layers import MapLayer
from pykarta.geometry import Point, BoundingBox, LineString, Polygon
import pykarta.draw

#============================================================================
# A container layer which can hold vector objects
#============================================================================
class MapVectorLayer(MapLayer):
	def __init__(self, tool_done_cb=None, obj_modified_cb=None):
		MapLayer.__init__(self)
		self.layer_objs = []
		self.visible_objs = []
		self.dragger = None
		self.drawing_tool = None
		self.tool_done_cb = tool_done_cb
		self.obj_modified_cb = obj_modified_cb

	def add_obj(self, obj):
		self.layer_objs.append(obj)
		self.set_stale()

	def remove_obj(self, obj):
		self.layer_objs.remove(obj)
		self.set_stale()

	def raise_obj(self, obj):
		self.layer_objs.remove(obj)
		self.layer_objs.append(obj)
		self.set_stale()

	def set_tool(self, tool):
		print "set_tool(%s)" % str(tool)
		#self.editing_off()
		self.drawing_tool = tool
		if tool:
			tool.activate(self)
			self.set_cursor(tool.cursor)
		else:
			self.set_cursor(None)

	# Turn on editing for the indicated object and move it to the top.
	def edit_obj(self, obj):
		obj.editable = True
		self.raise_obj(obj)

	# Disabling editing of all of the objects.
	def editing_off(self):
		for obj in self.layer_objs:
			obj.editable = False
		self.containing_map.queue_draw()

	# The drawing tools call this when they complete an operation.
	def drawing_tool_done(self, tool, obj):
		self.set_tool(None)
		# If there is no callback function or it returns False, do default action.
		if self.tool_done_cb is None or not self.tool_done_cb(tool, obj):
			if isinstance(tool, MapToolSelect):
				self.editing_off()
				obj.editable = True
				self.containing_map.queue_draw()
			elif isinstance(tool, MapToolDelete):
				self.remove_obj(obj)
			else:
				self.add_obj(obj)

	# Change the mouse cursor.
	def set_cursor(self, cursor):
		#print "cursor:", cursor
		if cursor is not None:
			cursor = gtk.gdk.Cursor(cursor)
		self.containing_map.set_cursor(cursor)

	# Viewport has changed
	def do_viewport(self):
		map_bbox = self.containing_map.get_bbox()
		self.visible_objs = []
		for obj in self.layer_objs:
			if obj.geometry.get_bbox().overlaps(map_bbox):
				obj.project(self.containing_map)
				self.visible_objs.append(obj)

	# Draw the objects selected by by do_viewport()
	def do_draw(self, ctx):
		for obj in self.visible_objs:
			obj.draw(ctx)
		if self.drawing_tool:
			self.drawing_tool.draw(ctx)

	# Mouse button pressed down while pointer is over map
	def on_button_press(self, gdkevent):
		if gdkevent.button == 1:
			if self.drawing_tool:
				x, y = self.snap_search(gdkevent, None, self.drawing_tool.snap)
				self.drawing_tool.on_button_press(x, y, gdkevent)
				self.containing_map.queue_draw()
				return True
			point = Point(gdkevent.x, gdkevent.y)
			for obj in reversed(self.visible_objs):
				if obj.editable:
					i = obj.point_hit_detect(gdkevent)
					if i is not None:
						self.dragger = MapDragger(obj, i)
						self.set_cursor(gtk.gdk.FLEUR)
						return True
		return False

	# Mouse pointer moving over map
	def on_motion(self, gdkevent):
		if self.drawing_tool:
			x, y = self.snap_search(gdkevent, None, self.drawing_tool.snap)
			self.drawing_tool.on_motion(x, y, gdkevent)
			self.containing_map.queue_draw()
			return True
		if self.dragger:
			snapped_x, snapped_y = self.snap_search(gdkevent, self.dragger.obj, self.dragger.obj.snap)
			self.dragger.obj.move(self.dragger.i, snapped_x, snapped_y, gdkevent)
			self.dragger.count += 1
			self.containing_map.queue_draw()
			return True
		return False

	# Mouse button released while pointer is over map
	def on_button_release(self, gdkevent):
		if gdkevent.button == 1:
			if self.drawing_tool:
				self.drawing_tool.on_button_release(gdkevent)
				self.containing_map.queue_draw()
				return True
			if self.dragger:
				if self.dragger.count > 0:
					self.dragger.obj.drop(self.dragger.i, self.containing_map)
				else:
					self.dragger.obj.delete(self.dragger.i, self.containing_map)
				if self.obj_modified_cb:
					self.obj_modified_cb(self.dragger.obj)
				self.dragger = None
				self.set_cursor(None)
				self.containing_map.queue_draw()
				return True
		return False

	# If an object has a point near the given event position, return that point.
	# Otherwise, return the event position.
	# If enable is False, this always returns the event position.
	# The paremeter source_obj refers to the object whose point may be snapped
	# to the points of surounding objects. We use it to skip that object during
	# the search.
	def snap_search(self, gdkevent, source_obj, enable):
		if enable:
			for obj in self.visible_objs:
				if obj is not source_obj:	
					snap = obj.snap_search(gdkevent)
					if snap:
						#print "Snap!"
						return snap
		return (gdkevent.x, gdkevent.y)

class MapDragger(object):
	def __init__(self, obj, i):
		self.obj = obj
		self.i = i
		self.count = 0

#============================================================================
# The objects
# This follow GeoJSON
#============================================================================

# Base class for vector objects
class MapVectorObj(object):
	snap = True		# snap this object's points to other objects
	min_points = 0
	unclosed = 1

	def __init__(self):
		self.editable = False
		self.geometry = None

	def project(self, containing_map):
		self.projected_points = containing_map.project_points(self.geometry.points)
		self.update_phantoms()

	# Should a click at the specified location (specified in both lat, lon space and pixel space)
	# be considered to have hit this object?
	def obj_hit_detect(self, lat_lon, gdkevent):
		return self.point_hit_detect(gdkevent, tolerance=15) is not None

	# Did this click hit one of the object's points?
	def point_hit_detect(self, gdkevent, tolerance=5):
		i = 0
		for point in self.projected_points:
			if abs(gdkevent.x - point[0]) <= tolerance and abs(gdkevent.y - point[1]) <= tolerance:
				return i
			i += 1
		i = 0
		for point in self.phantom_points:
			if abs(gdkevent.x - point[0]) <= tolerance and abs(gdkevent.y - point[1]) <= tolerance:
				self.projected_points.insert(i+1, self.phantom_points[i])
				self.geometry.points.insert(i+1, Point(0.0, 0.0))
				return i+1
			i += 1
		return None

	# Is this click close to one of the objects points? If so, return that point.
	def snap_search(self, gdkevent):
		for point in self.projected_points:
			if abs(gdkevent.x - point[0]) <= 10 and abs(gdkevent.y - point[1]) <= 10:
				return point
		return False

	# Move point i of the object to the location specified by x, y.
	def move(self, i, x, y, gdkevent):
		self.projected_points[i] = (x, y)
		self.update_phantoms()

	# Finalize the position of a moved point.
	def drop(self, i, containing_map):
		lat, lon = containing_map.unproject_point(*(self.projected_points[i]))
		self.geometry.points[i] = Point(lat, lon)
		self.geometry.bbox = None

	# Delete point i of this object.
	def delete(self, i, containing_map):
		if len(self.geometry.points) > self.min_points:
			self.geometry.points.pop(i)
			self.geometry.bbox = None
			self.projected_points.pop(i)
			self.update_phantoms()

	# Update the locations of the intermediate points which can be dragged to add points.
	def update_phantoms(self):
		i = 0
		self.phantom_points = []
		while i < (len(self.projected_points) - self.unclosed):
			p1 = self.projected_points[i]	
			p2 = self.projected_points[(i+1)%len(self.projected_points)]
			self.phantom_points.append(( (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2))
			i += 1

class MapVectorMarker(MapVectorObj):
	min_points = 1
	def __init__(self, point, style={}):
		MapVectorObj.__init__(self)
		self.geometry = LineString((point,))
		self.style = style
		self.symbol = None
		self.label = self.style.get("label")
	def project(self, containing_map):
		MapVectorObj.project(self, containing_map)
		if self.symbol is None:
			self.symbol = containing_map.symbols.get_symbol(self.style.get("symbol","Dot"),"Dot")
		self.symbol_renderer = self.symbol.get_renderer(containing_map)
	def draw(self, ctx):
		x, y = self.projected_points[0]
		self.symbol_renderer.blit(ctx, x, y)
		if self.label:
			pykarta.draw.poi_label(ctx, x+self.symbol_renderer.label_offset, y, self.label)

class MapVectorLineString(MapVectorObj):
	min_points = 2
	def __init__(self, line_string, style={}):
		MapVectorObj.__init__(self)
		if isinstance(line_string, LineString):
			self.geometry = line_string
		else:
			self.geometry = LineString(line_string)
		self.style = style
	def draw(self, ctx):
		pykarta.draw.line_string(ctx, self.projected_points)
		if self.style.get("arrows", False):
			pykarta.draw.line_string_arrows(ctx, self.projected_points)
		pykarta.draw.stroke_with_style(ctx, self.style)
		if self.editable:
			pykarta.draw.node_pluses(ctx, self.phantom_points, style={})
			pykarta.draw.node_dots(ctx, self.projected_points, style={})
		else:
			pykarta.draw.node_dots(ctx, self.projected_points, style={"diameter":2.0,"fill-color":(0.0,0.0,0.0,1.0)})

class MapVectorPolygon(MapVectorObj):
	min_points = 3
	unclosed = 0
	def __init__(self, polygon, style={}):
		MapVectorObj.__init__(self)
		if isinstance(polygon, Polygon):
			self.geometry = polygon
		else:
			self.geometry = Polygon(polygon)
		self.style = style
		self.label = self.style.get("label",None)
		self.label_center = None
		self.projected_label_center = None
	def set_label(self, label):
		self.label = label
	def get_label_center(self):
		if self.label_center is None:
			self.label_center = self.geometry.choose_label_center()
		return self.label_center
	def project_label_center(self, containing_map):
		if self.label:
			self.projected_label_center = containing_map.project_point(self.get_label_center())
	def project(self, containing_map):
		MapVectorObj.project(self, containing_map)
		self.project_label_center(containing_map)
	def draw(self, ctx):
		pykarta.draw.polygon(ctx, self.projected_points)
		pykarta.draw.fill_with_style(ctx, self.style)
		pykarta.draw.stroke_with_style(ctx, self.style)
		if self.editable:
			pykarta.draw.node_pluses(ctx, self.phantom_points, style={})
			pykarta.draw.node_dots(ctx, self.projected_points, style={})
		else:
			pykarta.draw.node_dots(ctx, self.projected_points, style={"diameter":2.0,"fill-color":(0.0,0.0,0.0,1.0)})
		if self.label and self.projected_label_center:
			x, y = self.projected_label_center
			pykarta.draw.centered_label(ctx, x, y, self.label)
	def obj_hit_detect(self, lat_lon, gdkevent):
		return self.geometry.contains_point(lat_lon)
	def drop(self, i, containing_map):
		MapVectorObj.drop(self, i, containing_map)
		self.label_center = None
		self.project_label_center(containing_map)
	def delete(self, i, containing_map):
		MapVectorObj.delete(self, i, containing_map)
		self.label_center = None
		self.project_label_center(containing_map)

class MapVectorBoundingBox(MapVectorObj):
	snap = False
	min_points = 4
	x_map = (3, 2, 1, 0)
	y_map = (1, 0, 3, 2)
	def __init__(self, bbox, style={}):		# FIXME: style is ignored
		MapVectorObj.__init__(self)
		self.orig_bbox = bbox
		self.geometry = Polygon((
			Point(bbox.max_lat, bbox.min_lon),		# NW
			Point(bbox.max_lat, bbox.max_lon),		# NE
			Point(bbox.min_lat, bbox.max_lon),		# SE
			Point(bbox.min_lat, bbox.min_lon),		# SW
			))
	def obj_hit_detect(self, lat_lon, gdkevent):
		return self.geometry.get_bbox().contains_point(lat_lon)
	def snap_search(self, gdkevent):
		# Snapping to bounding boxes does not make sense.
		return None
	def draw(self, ctx):
		pykarta.draw.polygon(ctx, self.projected_points)
		pykarta.draw.stroke_with_style(ctx, {"dash-pattern":(3,2)})
		if self.editable:
			pykarta.draw.node_dots(ctx, self.projected_points)
	def update_phantoms(self):
		self.phantom_points = []
	def move(self, i, x, y, gdkevent):
		# Figure out by how much the dragged point will move.
		start_x, start_y = self.projected_points[i]
		x_dist = x - start_x
		y_dist = y - start_y
		# Move the dragged point.
		self.projected_points[i] = (x, y)
		# Move the points at the nearest corners by the same amount, each along only one axis.
		x_i = self.x_map[i]
		self.projected_points[x_i] = (self.projected_points[x_i][0] + x_dist, self.projected_points[x_i][1])
		y_i = self.y_map[i]
		self.projected_points[y_i] = (self.projected_points[y_i][0], self.projected_points[y_i][1] + y_dist)
	def drop(self, i, containing_map):
		self.geometry.points = containing_map.unproject_points(self.projected_points)
		self.orig_bbox.reset()
		self.orig_bbox.add_points(self.geometry.points)
		self.geometry.bbox = None	# recompute

#============================================================================
# The drawing tools
#============================================================================

class MapToolBase(object):
	snap = False
	cursor = None
	def __init__(self, style={}):
		self.style = style
		self.layer = None
	def activate(self, layer):
		self.layer = layer
	def on_button_press(self, x, y, gdkevent):
		pass	
	def on_motion(self, x, y, gdkevent):
		self.hover_point = (x, y)
	def on_button_release(self, gdkevent):
		pass
	def draw(self, ctx):
		pass

class MapToolSelectBase(MapToolBase):
	snap = False
	def on_button_press(self, x, y, gdkevent):
		lat, lon = self.layer.containing_map.unproject_point(x, y)
		lat_lon = Point(lat, lon)
		#print "Button press", type(self), x, y, lat, lon
		for obj in reversed(self.layer.visible_objs):
			#print " ", obj
			if obj.obj_hit_detect(lat_lon, gdkevent):
				#print "  Hit!"
				self.done(obj)
				break
	def done(self, obj):
		self.layer.drawing_tool_done(self, obj)

class MapToolSelect(MapToolSelectBase):
	cursor = gtk.gdk.HAND1

class MapToolDelete(MapToolSelectBase):
	cursor = gtk.gdk.X_CURSOR

class MapDrawBase(MapToolBase):
	def activate(self, layer):
		MapToolBase.activate(self, layer)
		self.points = None
		self.projected_points = []
		self.hover_point = None
	def on_button_press(self, x, y, gdkevent):
		self.projected_points.append((x, y))
		if gdkevent.state & gtk.gdk.SHIFT_MASK:
			self.done()
	def on_motion(self, x, y, gdkevent):
		self.hover_point = (x, y)
	def done(self):
		self.points = self.layer.containing_map.unproject_points(self.projected_points)
		self.layer.drawing_tool_done(self, self.create_vector_object())
	def create_vector_object(self):
		return None

class MapDrawMarker(MapDrawBase):
	snap = True
	cursor = gtk.gdk.PENCIL
	def on_button_press(self, x, y, gdkevent):
		self.projected_points.append((x, y))
		self.done()
	def create_vector_object(self):
		return MapVectorMarker(self.points[0], self.style)

class MapDrawLineString(MapDrawBase):
	snap = True
	cursor = gtk.gdk.PENCIL
	def draw(self, ctx):
		if len(self.projected_points) > 1:
			pykarta.draw.line_string(ctx, self.projected_points)
			pykarta.draw.stroke_with_style(ctx, self.style)
		if len(self.projected_points) > 0:
			pykarta.draw.node_dots(ctx, self.projected_points)
			ctx.move_to(*(self.projected_points[-1]))
			ctx.line_to(*(self.hover_point))
			pykarta.draw.stroke_with_style(ctx, {"dash-pattern":(3,2)})
	def create_vector_object(self):
		return MapVectorLineString(self.points, self.style)

class MapDrawPolygon(MapDrawBase):
	snap = True
	cursor = gtk.gdk.PENCIL
	def draw(self, ctx):
		if len(self.projected_points) > 1:
			pykarta.draw.line_string(ctx, self.projected_points)
			pykarta.draw.fill_with_style(ctx, self.style)
			pykarta.draw.stroke_with_style(ctx, self.style)
		if len(self.projected_points) > 0:
			pykarta.draw.node_dots(ctx, self.projected_points)
			ctx.move_to(*(self.projected_points[-1]))
			ctx.line_to(*(self.hover_point))
			pykarta.draw.stroke_with_style(ctx, {"dash-pattern":(3,2)})
	def create_vector_object(self):
		return MapVectorPolygon(self.points, self.style)

class MapDrawBoundingBox(MapDrawBase):
	cursor = gtk.gdk.SIZING
	def on_button_press(self, x, y, gdkevent):
		self.projected_points = [(gdkevent.x, gdkevent.y)]	# no snapping
	def on_motion(self, x, y, gdkevent):
		self.hover_point = (gdkevent.x, gdkevent.y)			# no snapping
	def on_button_release(self, gdkevent):
		self.projected_points.append(self.hover_point)
		self.done()
	def draw(self, ctx):
		if len(self.projected_points) > 0 and self.hover_point:
			start_x, start_y = self.projected_points[0]
			hover_x, hover_y = self.hover_point
			ctx.rectangle(start_x, start_y, hover_x - start_x, hover_y - start_y)
			pykarta.draw.stroke_with_style(ctx, {"dash-pattern":(3,2)})
	def create_vector_object(self):
		bbox = BoundingBox()
		bbox.add_points(self.points)
		return MapVectorBoundingBox(bbox)

