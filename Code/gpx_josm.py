# gpx_josm.py
# Copyright 2013, 2014, Trinity College
# Last modified: 19 September 2014

import StringIO

from gpx_data_gpx import GpxWaypoint
from pykarta.formats.osm_writer import OsmWriter
from pykarta.geometry import Point, BoundingBox

# Convert Garmin GPX <sym> values into OSM tags
# This code is outside of gpx_gui.py because it is long.
sym_to_tags = {
	"Car": {							# Probably actually means "where I left my car" See "Parking Area"
		"amenity": "parking",
		},
	"Department Store": {
		"shop": "department_store",
		},
	"Gas Station": {
		"amenity": "fuel",
		},
	"Medical Facility": {
		"name": "Medical Facility",
		"amenity": "hospital",
		},
	"Parking Area": {
		"amenity": "parking",
		},
	"Residence": {
		"building": "yes",
		},
	"Restroom": {
		"amenity": "toilets",
		},
	"Shopping Center": {
		"shop": "mall",
		},
	"School":  {
		"amenity": "school",
		},
	"Telephone": {
		"amenity": "telephone",
		},
	"Truck Stop": {
		"name": "Truck Stop",
		"amenity": "parking",
		},
	}

# Convert a GPX object to an OSM object, make it available as in OSM
# file from our internal web server, and ask JOSM to add it to the map.
# FIXME: implement conversion of routes to ways
# NOTE: JOSM now has a command to do this without downloading a file
def add_obj(obj, ui, josm, server):
	print "Add object in JOSM:", obj

	if type(obj) is not GpxWaypoint:
		ui.error(_("Only waypoints can be sent to JOSM"))
		return

	# Create an OSM XML file containing the desired point.
	fh = StringIO.StringIO()
	osm = OsmWriter(fh, "GPX Trip Planner")
	tags = sym_to_tags.get(obj.sym, {})
	osm.new_node(obj.lat, obj.lon, tags)
	osm.save()
	osm_text = fh.getvalue()

	# Ask our internal HTTP server to dispense the text of the
	# OSM XML file when JOSM asks for it. The HTTP server gives us
	# the URL to pass to JOSM.
	temp_url = server.add_temp(osm_text)

	# Create a bounding box to describe a small area around the new point.
	bbox = BoundingBox()
	bbox.add_point(Point(obj.lat + 0.001, obj.lon - 0.001))
	bbox.add_point(Point(obj.lat - 0.001, obj.lon + 0.001))

	josm.cmd_zoom(bbox)
	josm.send_cmd("import", {'url': temp_url})

