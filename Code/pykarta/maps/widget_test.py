#! /usr/bin/python

import gtk
import gobject
import time

from pykarta.maps.widget import MapWidget, MapPrint
from pykarta.geometry import Point, BoundingBox
from pykarta.maps.layers import MapLayer, MapTileLayerDebug, MapLayerScale, MapLayerAttribution
from pykarta.maps.layers.vector import MapVectorLayer, \
	MapVectorMarker, \
	MapVectorLineString, \
	MapVectorPolygon, \
	MapVectorBoundingBox, \
	MapToolSelect, \
	MapToolDelete, \
	MapDrawMarker, \
	MapDrawLineString, \
	MapDrawPolygon, \
	MapDrawBoundingBox
from pykarta.maps.layers.marker import MapMarkerLayer
from pykarta.maps.layers.shapefile import MapShapefileLayer
from pykarta.maps.layers.mapquest import MapTrafficLayer

#-------------------------------------------------------------------------
# A layer
#-------------------------------------------------------------------------
class TestLayer(MapLayer):
	def do_viewport(self):
		print "Test layer: new viewport:", self.containing_map.get_bbox_degrees()
		points = (Point(42.125,-72.75), Point(42.125,-72.70), Point(42.10,-72.70))
		self.points_projected = self.containing_map.project_points(points)

	def do_draw(self, ctx):
		print "Test layer: redraw"
		ctx.set_source_rgb(0.0, 0.0, 0.0)
		ctx.set_line_width(1)
		ctx.move_to(*self.points_projected[0])
		for p in self.points_projected[1:]:
			ctx.line_to(*p)
		ctx.stroke()

#-------------------------------------------------------------------------
# Called when Print button is pressed
#-------------------------------------------------------------------------
def on_print(widget, map_widget):
	p = MapPrint(map_widget)
	print p.do_print()

#-------------------------------------------------------------------------
# Called when a vector drawing operation is completed
#-------------------------------------------------------------------------
drag_button = None
def vector_draw_cb(tool, obj):
	print tool, obj
	drag_button.set_active(True)
	return False

#-------------------------------------------------------------------------
# Main Window
#-------------------------------------------------------------------------
gobject.threads_init()
window = gtk.Window()
window.set_default_size(800, 800)
window.connect('delete-event', lambda window, event: gtk.main_quit())
main_box = gtk.HBox()
window.add(main_box)

# Map widget
map_widget = MapWidget(
	#tile_source = "osm-default-svg",
	#tile_source=["mapquest-openaerial", "stamen-toner-labels"],
	#tile_source="bing-road",
	)
main_box.pack_start(map_widget)
map_widget.set_center_and_zoom(42.125, -72.75, 12)
#map_widget.add_layer("test", TestLayer())
map_widget.add_osd_layer(MapLayerScale())
map_widget.add_osd_layer(MapLayerAttribution())
#map_widget.set_rotation(True)

map_widget.symbols.add_symbol("./gpx_syms/other/Dot.svg")

# Add vector layer
vector = MapVectorLayer(vector_draw_cb)
map_widget.add_layer("vector", vector)
vector.add_obj(MapVectorMarker(Point(42.125, -72.73), {"label":"a house"}))
vector.add_obj(MapVectorPolygon([Point(42.125, -72.75), Point(42.2, -72.75), Point(42.125, -72.8)]))
vector.add_obj(MapVectorLineString([Point(42.120, -72.80), Point(42.10, -72.73), Point(42.115, -72.745)]))
bbox = BoundingBox()
bbox.add_point(Point(42.125, -72.70))
bbox.add_point(Point(42.10, -72.65))
vector.add_obj(MapVectorBoundingBox(bbox))

# Add marker layer
if False:
	marker = MapMarkerLayer()
	map_widget.add_layer("marker", marker)
	marker.add_marker(42.13, -72.75, "Dot", "a marker")
	marker.add_marker(42.13, -72.74, "Dot", "a marker")
	marker.add_marker(42.13, -72.73, "Dot", "a marker")
	marker.add_marker(42.13, -72.72, "Dot", "a marker")

# Add shapefile layer
if False:
	trails = MapShapefileLayer("../../../../massgis/longdisttrails/LONGDISTTRAILS_ARC_4326")
	map_widget.add_layer("trails", trails)

# Add traffic layer
if False:
	traffic = MapTrafficLayer()
	map_widget.add_layer("traffic", traffic)

if False:
	tile_debug = MapTileLayerDebug()
	map_widget.add_layer("tile_debug", tile_debug)

# Bottom bar
button_bar = gtk.VBox()
main_box.pack_start(button_bar, False, False)

tools =	(
		("Drag Map", None),
		("Select for Editing", MapToolSelect()),
		("Delete", MapToolDelete()),
		("Marker", MapDrawMarker({"label":"New Point"})),
		("Line String", MapDrawLineString()),
		("Polygon", MapDrawPolygon()),
		("BBox", MapDrawBoundingBox()),
		)
tool_i = 0
for name, obj in tools:
	button = gtk.RadioButton(group=drag_button, label=name)
	if drag_button is None:
		drag_button = button
	button_bar.pack_start(button, False, False)
	button.connect("toggled", lambda widget, i: not widget.get_active() or vector.set_tool(tools[i][1]), tool_i)
	tool_i += 1

# Print button
button = gtk.Button(label="Print")
button_bar.pack_start(button, False, False)
button.connect("clicked", on_print, map_widget)

window.show_all()

# Benchmark projection
# Started at 4.6 seconds
import timeit
point = Point(42.00, -72.00)
points = []
for i in range(10000):
	points.append(point)
print timeit.timeit('map_widget.project_points(points)', number=100, setup="from __main__ import map_widget, points")

gtk.main()

