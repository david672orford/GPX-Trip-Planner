#=============================================================================
# gpx_layer.py
# Base for the editable vector layers
# Similiar pykarta/maps/layers/vector.py but MVC style
# Copyright 2013, 2014, Trinity College
# Last modified: 18 December 2014
#=============================================================================

from pykarta.maps.layers import MapLayer

class GpxEditableLayer(MapLayer):
	def __init__(self):
		MapLayer.__init__(self)
		self.drawing_tool = None
		self.layer_objs = None
		self.visible_objs = []
		self.selected_path = None

	# Called whenever the selection is changed by a viewer other than this one.
	def on_select(self, path, source, client_name):
		self.selected_path = path
		self.redraw()

	def select(self, path):
		self.selected_path = path
		self.layer_objs.select(path, "map_layer")
		self.redraw()

	# User has selected indicated tool on the toolbar
	# or None if this layer has lost editing focus.
	def set_tool(self, tool):
		if tool == "tool_select_adjust":
			self.drawing_tool = self.create_tool_select_adjust()
		elif tool == "tool_draw":
			self.drawing_tool = self.create_tool_draw()
		elif tool == "tool_delete":
			self.drawing_tool = self.create_tool_delete()
		else:
			self.drawing_tool = None
		self.select(None)
		return ""

	def create_tool_select_adjust(self):
		raise NotImplementedError

	def create_tool_draw(self):
		raise NotImplementedError

	def create_tool_delete(self):
		raise NotImplementedError

	# Identify the objects which are within the viewport determine which
	# of them should be rendered (based on other criteria), and create
	# renders for them in self.visible_objs.
	def do_viewport(self):
		map_bbox = self.containing_map.get_bbox()
		self.visible_objs = []
		index = 0
		for obj in self.layer_objs:
			if obj.gpxtp_show and obj.get_bbox().overlaps(map_bbox):
				renderer = self.create_renderer(obj, index)
				if renderer is not None:
					self.visible_objs.append(renderer)
			index += 1
		self.containing_map.feedback.debug(1, " %s: %d of %d objects visible" % (self.__class__.__name__, len(self.visible_objs), len(self.layer_objs)))

	# All objects which are within the viewport will be passed to this
	# function. If it wants to render the object, it will create a
	# renderer object instance which do_draw() can call to render 
	# the object. Otherwise ti will return None.
	def create_renderer(self, obj, index):
		return None

	# Draw the objects which do_viewport() determined are visible.
	def do_draw(self, ctx):
		for obj in self.visible_objs:
			obj.draw(ctx, self.selected_path)
		if self.drawing_tool is not None:
			self.drawing_tool.draw(ctx)

	# Mouse button down
	def on_button_press(self, gdkevent):
		if gdkevent.button == 1 and self.drawing_tool is not None:
			return self.drawing_tool.on_button_press(gdkevent)
		return False

	# Mouse pointer moved
	def on_motion(self, gdkevent):
		if self.drawing_tool is not None:
			return self.drawing_tool.on_motion(gdkevent)
		return False

	# Mouse button up
	def on_button_release(self, gdkevent):
		if gdkevent.button == 1 and self.drawing_tool is not None:
			return self.drawing_tool.on_button_release(gdkevent)
		return False

class GpxTool(object):
	def on_button_press(self, gdkevent):
		pass
	def on_motion(self, gdkevent):
		pass
	def on_button_release(self, gdkevent):
		pass
	def draw(self, ctx):
		pass

def points_close(p1, p2, tolerance=10):
	return abs(p1[0] - p2[0]) <= tolerance and abs(p1[1] - p2[1]) <= tolerance

