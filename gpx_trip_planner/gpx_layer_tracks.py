#=============================================================================
# gpx_layer_tracks.py
# Track map layer
# Copyright 2013--2023, Trinity College
# Last modified: 26 March 2023
#=============================================================================

from gi.repository import Gtk
import math
import cairo

from gpx_layer import GpxEditableLayer, GpxTool, points_close
import pykarta.geometry
import pykarta.draw
import gpx_colors

class TrackLayer(GpxEditableLayer):
	def __init__(self, gpx_data):
		GpxEditableLayer.__init__(self)

		# Two-way connexion between this layer and data store
		self.layer_objs = gpx_data.tracks
		self.layer_objs.add_client("map_layer", self)

		self.radius = 4
		self.arrow_show_level = 14
		self.point_show_level = 15
		self.point_zoom_level = 16

	def on_select(self, path, source, client_name):
		self.selected_path = path

		if path is not None and source != 'picker':
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
	
		GpxEditableLayer.on_select(self, path, source, client_name)

	# Override do_viewport() because he have to handle two levels.
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
						self.visible_objs.append(self.create_renderer((track, track_segment), (track_i, trackseg_i)))
					trackseg_i += 1
					trackseg_count += 1
			track_i += 1
		self.containing_map.feedback.debug(1, " %d of %d track segments in view" % (len(self.visible_objs), trackseg_count))

	def create_renderer(self, obj, index):
		class TrackRenderer(object):
			def __init__(self, obj, index, layer):
				self.track, self.track_segment = obj
				self.track_i, self.trackseg_i = index
				self.layer = layer
				containing_map = layer.containing_map
				self.color = gpx_colors.rgb_by_name.get(self.track.gpxx_DisplayColor, (1.0, 0.0, 0.0, 1.0))
				self.projected_points = containing_map.scale_points(
					self.track_segment.get_projected_simplified_points(containing_map.get_zoom())
					)
				self.zoom = containing_map.get_zoom()
			def draw(self, ctx, selected_path):

				if selected_path and selected_path[0] == self.track_i:
					line_width = 4
				else:
					line_width = 2
	
				# Draw track line
				pykarta.draw.line_string(ctx, self.projected_points)
				ctx.set_line_width(line_width)
				ctx.set_source_rgba(*self.color)
				ctx.set_line_join(cairo.LINE_JOIN_ROUND)
				ctx.stroke()
				ctx.set_line_join(cairo.LINE_JOIN_MITER)
	
				# If zoomed in far enough, draw direction of travel arrows
				if self.zoom > self.layer.arrow_show_level:
					pykarta.draw.line_string_arrows(ctx, self.projected_points, line_width=line_width)
					ctx.stroke()
	
				# If this layer is active and map is zoomed in far enough, draw track point markers.
				if self.layer.drawing_tool is not None and self.zoom >= self.point_show_level:
					point_i = 0
					for point in points:
						if selected_path == (self.track_i, self.trackseg_i, point_i):
							ctx.arc(point[0], point[1], self.radius-1, 0, 2*math.pi)
							ctx.set_line_width(4)
						else:
							ctx.arc(point[0], point[1], self.radius, 0, 2*math.pi)
							ctx.set_line_width(1)
						ctx.set_source_rgba(*self.color)
						ctx.stroke_preserve()
						ctx.set_source_rgb(1.0, 1.0, 1.0)		# white
						ctx.fill()
						point_i += 1
		return TrackRenderer(obj, index, self)

	def create_tool_select_adjust(self):
		class TrackpointSelector(GpxTool):
			def __init__(self, layer):
				self.layer = layer
			def on_button_press(self, gdkevent):
				if self.zoom >= self.layer.point_show_level:
					event_point = (gdkevent.x, gdkevent.y)
					for segment in self.layer.visible_objs:
						point_i = 0
						for point in segment.projected_points:
							if points_close(point, event_point):
								print("Hit track point")
								self.layer.select((segment.track_i, segment.trackseg_i, point_i))
								return True
							point_i += 1
				return False

