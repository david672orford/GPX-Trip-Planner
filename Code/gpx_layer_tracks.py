#=============================================================================
# gpx_layer_tracks.py
# Track map layer
# Copyright 2013, Trinity College
# Last modified: 5 July 2013
#=============================================================================

import gtk
import math
import cairo

from gpx_layer import GpxVectorLayer
import pykarta.geometry
import pykarta.draw
import gpx_colors

class TrackLayer(GpxVectorLayer):
	def __init__(self, gpx_data):
		GpxVectorLayer.__init__(self)

		# Two-way connexion between this layer and data store
		self.layer_objs = gpx_data.tracks
		self.layer_objs.add_client("map_layer", self)

		self.radius = 4
		self.arrow_show_level = 14
		self.point_show_level = 15
		self.point_zoom_level = 16

		self.selected_path = None

	def on_select(self, path, source, client_name):
		self.selected_path = path

		if path != None and source != 'picker':
			if len(path) == 3:		# click on single point
				point = self.layer_objs[path[0]][path[1]][path[2]]
				zoom = self.containing_map.get_zoom()
				if zoom < self.point_zoom_level:
					zoom = self.point_zoom_level
				self.containing_map.set_center_and_zoom(point.lat, point.lon, zoom)
			else:
				bbox = pykarta.geometry.BoundingBox()
				if len(path) == 1:		# click on an entire track
					track_obj = self.layer_objs[path[0]]
					for track_seg in track_obj:
						for point in track_seg:
							bbox.add_point(pykarta.geometry.Point(point.lat, point.lon))
				else:					# click on an entire track segment
					track_seg = self.layer_objs[path[0]][path[1]]
					for point in track_seg:
						bbox.add_point(pykarta.geometry.Point(point.lat, point.lon))
				self.containing_map.zoom_to_extent(bbox)
	
		self.containing_map.queue_draw()	

	def set_tool(self, tool):
		if tool != None and tool != "tool_select":
			raise NotImplementedError
		GpxVectorLayer.set_tool(self, tool)
		return _("Click to select track points.")

	def do_viewport(self):
		map_bbox = self.containing_map.get_bbox()
		zoom = self.containing_map.get_zoom()
		self.visible_objs = []
		track_i = 0
		trackseg_count = 0
		for track in self.layer_objs:
			if track.gpxtp_show:
				trackseg_i = 0
				for track_segment in track:
					if track_segment.get_bbox().overlaps(map_bbox):
						color = gpx_colors.rgb_by_name.get(track.gpxx_DisplayColor, (1.0, 0.0, 0.0, 1.0))
						points = self.containing_map.scale_points(track_segment.get_projected_simplified_points(zoom))
						self.visible_objs.append([track_i, trackseg_i, points, color])
					trackseg_i += 1
					trackseg_count += 1
			track_i += 1
		self.containing_map.feedback.debug(1, " %d of %d track segments in view" % (len(self.visible_objs), trackseg_count))

	def do_draw(self, ctx):
		zoom = self.containing_map.get_zoom()

		# Step through the visible track segments
		for segment in self.visible_objs:
			track_i, trackseg_i, points, color = segment

			if self.selected_path and self.selected_path[0] == track_i:
				line_width = 4
			else:
				line_width = 2

			# Draw track line
			pykarta.draw.line_string(ctx, points)
			ctx.set_line_width(line_width)
			ctx.set_source_rgba(*color)
			ctx.set_line_join(cairo.LINE_JOIN_ROUND)
			ctx.stroke()
			ctx.set_line_join(cairo.LINE_JOIN_MITER)

			# If zoomed in far enough, draw direction of travel arrows
			if zoom > self.arrow_show_level:
				pykarta.draw.line_string_arrows(ctx, points, line_width=line_width)
				ctx.stroke()

			# If this layer is active and map is zoomed in far enough, draw track point markers.
			if self.tool != None and zoom >= self.point_show_level:
				point_i = 0
				for point in points:
					if self.selected_path == (track_i, trackseg_i, point_i):
						ctx.arc(point[0], point[1], self.radius-1, 0, 2*math.pi)
						ctx.set_line_width(4)
					else:
						ctx.arc(point[0], point[1], self.radius, 0, 2*math.pi)
						ctx.set_line_width(1)
					ctx.set_source_rgba(*color)
					ctx.stroke_preserve()
					ctx.set_source_rgb(1.0, 1.0, 1.0)		# white
					ctx.fill()
					point_i += 1

	def on_button_press(self, gdkevent):
		# If this layer is not active, we are done.
		if self.tool == None:
			return False

		# If not single click with left button, we are done.
		if gdkevent.type != gtk.gdk.BUTTON_PRESS or gdkevent.button != 1:
			return False

		# If tracks are not shown at this zoom level, we are done.
		if self.containing_map.get_zoom() < self.point_show_level:
			return False

		# If user hit a track point, select it.
		for segment in self.visible_objs:
			track_i, trackseg_i, points, color = segment
			point_i = 0
			for point in points:
				x, y = point
				if abs(gdkevent.x - x) <= self.radius and abs(gdkevent.y - y) <= self.radius:
					print "Hit track point"
					self.selected_path = (track_i, trackseg_i, point_i)
					self.layer_objs.select(self.selected_path, "map_layer")
					self.containing_map.queue_draw()
					return True
				point_i += 1

		return False

