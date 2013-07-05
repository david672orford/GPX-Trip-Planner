# pykarta/maps/layers/marker.py
# A simple marker layer
# Last modified: 5 April 2013

from pykarta.maps.layers import MapLayer
from pykarta.draw import poi_label
from pykarta.geometry import Point, BoundingBox
from pykarta.maps.projection import project_to_tilespace

class MapMarker(object):
	__slots__ = ('lat', 'lon', 'x', 'y', 'symbol', 'label')

class MapMarkerLayer(MapLayer):
	def __init__(self):
		MapLayer.__init__(self)
		self.index_zoom = 14
		self.markers = {}
		self.markers_count = 0
		self.visible_markers = []
		self.slop = 0.2
		self.zoom_min = 10
		self.label_zoom_min = 13

	# Add a marker to the layer. Markers are indexed according the tile
	# on which they fall at the the zoom level indicated by self.index_zoom.
	def add_marker(self, lat, lon, symbol=None, label=None):
		marker = MapMarker()
		marker.lat = lat
		marker.lon = lon
		marker.x, marker.y = project_to_tilespace(lat, lon, self.index_zoom)
		marker.symbol = self.containing_map.symbols.get_symbol(symbol, "Dot")
		marker.label = label

		key = (int(marker.x), int(marker.y))
		print "marker:", key
		if key not in self.markers:
			self.markers[key] = []
		self.markers[key].append(marker)

		self.markers_count += 1

	def get_bbox(self):
		bbox = BoundingBox()
		for marker_group in self.markers.values():
			for marker in marker_group:
				bbox.add_point(Point(marker.lat, marker.lon))
		return bbox

	def do_viewport(self):
		zoom = self.containing_map.get_zoom()
		self.visible_markers = []
		if zoom >= self.zoom_min:
			zoom_in = 2 ** (self.index_zoom - zoom)
			tlx, tly = self.containing_map.top_left_pixel
			tx_start = int((tlx-self.slop) * zoom_in)
			ty_start  = int((tly-self.slop) * zoom_in)
			tx_stop = int((tlx + self.containing_map.width / 256.0 + self.slop) * zoom_in + 0.999)
			ty_stop = int((tly + self.containing_map.height / 256.0 + self.slop) * zoom_in + 0.999)
			for x in range(tx_start, tx_stop+1):
				for y in range(ty_start, ty_stop+1):
					#print "viewport:", x, y
					for marker in self.markers.get((x, y), []):
						self.visible_markers.append((
							int((marker.x / zoom_in - tlx) * 256.0),
							int((marker.y / zoom_in - tly) * 256.0),
							marker.symbol.get_renderer(self.containing_map),
							marker
							))
			#print " %d of %d markers visible" % (len(self.visible_markers), self.markers_count)
				
	def do_draw(self, ctx):
		zoom = self.containing_map.get_zoom()
		for x, y, renderer, marker in self.visible_markers:
			#print " blit:", x, y
			renderer.blit(ctx, x, y)
			if marker.label and zoom >= self.label_zoom_min:
				poi_label(ctx, x+renderer.label_offset, y, marker.label)

