#=============================================================================
# gpx_layer_search.py
# Search results map layer
# Copyright 2013, Trinity College
# Last modified: 1 May 2013
#=============================================================================

import math
import gtk

from gpx_layer import GpxVectorLayer

class SearchLayer(GpxVectorLayer):
	def __init__(self, data):
		GpxVectorLayer.__init__(self)

		self.layer_objs = data
		self.layer_objs.add_client('map_layer', self)

		self.radius = None
	
	def on_select(self, path, source, client_name):
		self.selected_path = path
		if path != None:
			match = self.layer_objs[path[0]]
			if source == 'treeview_double_click':
				self.containing_map.set_center_and_zoom_in(match.lat, match.lon, match.zoom)
			else:
				self.containing_map.make_visible(match.lat, match.lon)
			if match.polygonpoints:
				self.containing_map.make_visible_polygon(match.polygonpoints)
		self.containing_map.queue_draw()

	def set_tool(self, tool):
		if tool != None and tool != "tool_select":
			raise NotImplementedError
		GpxVectorLayer.set_tool(self, tool)
		return _("Search result locations are circled on map. Click on them.")

	def do_viewport(self):
		self.visible_objs = []
		match_index = 0
		for match in self.layer_objs:
			x, y = self.containing_map.project_point(match)
			if x > 0 and x < self.containing_map.width and y > 0 and y < self.containing_map.height:	# if within viewport,
				polygonpoints = self.containing_map.project_points(match.polygonpoints)
				self.visible_objs.append([match_index, match, x, y, polygonpoints])
			match_index += 1
		self.containing_map.feedback.debug(1, " %d of %d search results are in view" % (len(self.visible_objs), len(self.layer_objs)))

	def do_draw(self, ctx):
		zoom = self.containing_map.get_zoom()
		self.radius = 3 + 2 * zoom

		for item in self.visible_objs:
			(match_index, match, x, y, polygonpoints) = item

			if len(polygonpoints) == 0:			# if point, draw magnifying glass
				# Lens
				ctx.arc(x, y, self.radius, 0, 2*math.pi)
				ctx.set_source_rgba(1.0, 1.0, 1.0, 0.5)
				ctx.fill_preserve()
	
				# Add handle
				ctx.move_to(x+0.707*self.radius, y+0.707*self.radius)
				ctx.line_to(x+2*self.radius, y+2*self.radius)
	
				# Stroke in one of two colors
				ctx.set_line_width(1 + zoom * 0.25)
				if self.selected_path != None and match_index == self.selected_path[0]:
					ctx.set_source_rgb(1.0, 0.0, 0.0)	# red
				else:
					ctx.set_source_rgb(0.0, 0.0, 0.0)	# black
				ctx.stroke()

			else:								# if boundary, draw it
				ctx.move_to(polygonpoints[0][0], polygonpoints[0][1])
				for point in polygonpoints[1:]:
					ctx.line_to(point[0], point[1])
				ctx.set_line_width(3)
				if self.selected_path != None and match_index == self.selected_path[0]:
					ctx.set_source_rgb(1.0, 0.0, 0.0)	# red
				else:
					ctx.set_source_rgb(0.0, 0.0, 0.0)	# black
				ctx.stroke()

	def on_button_press(self, gdkevent):
		if self.tool == None:
			return False

		# If not a single click with left button, bail out.
		if gdkevent.type != gtk.gdk.BUTTON_PRESS or gdkevent.button != 1:
			return False

		for item in reversed(self.visible_objs):
			(match_index, match, x, y, polygonpoints) = item
			if abs(gdkevent.x - x) <= self.radius and abs(gdkevent.y - y) <= self.radius:
				print "Hit search result point"
				self.selected_path = (match_index,)
				self.layer_objs.select(self.selected_path, "map_layer")
				self.containing_map.queue_draw()
				return True

		return False

