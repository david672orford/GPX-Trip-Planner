# pykarta/maps/layers/shapefile.py
# Display ESRI shapefiles
# Copyright 2013, Trinity College
# Last modified: 4 April 2013

from pykarta.formats.shapefile import Reader
from pykarta.maps.layers import MapLayer
import pykarta.draw
from pykarta.geometry import Point, BoundingBox

class MapShapefileLayer(MapLayer):
	def __init__(self, shapefile):
		MapLayer.__init__(self)
		self.sf = Reader(shapefile)
		self.visible_objs = []

	def do_viewport(self):
		map_bbox = self.containing_map.get_bbox()
		self.visible_objs = []
		for shape in self.sf.shapes():
			if shape.shapeType == 3:	# polyline
				shape_bbox = BoundingBox(shape.bbox)
				if shape_bbox.overlaps(map_bbox):
					points = map(lambda p: Point(p[1], p[0]), shape.points)
					self.visible_objs.append(self.containing_map.project_points(points))	

	def do_draw(self, ctx):
		ctx.set_line_width(1)
		ctx.set_source_rgba(0.0, 0.0, 0.0, 1.0)
		for obj in self.visible_objs:
			pykarta.draw.line_string(ctx, obj)
			ctx.stroke()

