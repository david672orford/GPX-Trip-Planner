# gpx_josm.py
# Copyright 2013, 2014, Trinity College
# Last modified: 1 August 2014

import urllib
import urllib2
import StringIO

from gpx_data_gpx import GpxWaypoint
from pykarta.formats.osm_writer import OsmWriter

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

def sync_view(bbox):
	print "Sync JOSM:", str(bbox)
	try:
		josm_remote("zoom", "top=%f&left=%f&bottom=%f&right=%f" % (bbox.max_lat, bbox.min_lon, bbox.min_lat, bbox.max_lon))
	except urllib2.HTTPError:
		ui.error(_("JOSM Remote Control command failed."))

def sync_view_and_load(bbox):
	print "Sync JOSM and load data:", bbox
	try:
		josm_remote("load_and_zoom", "top=%f&left=%f&bottom=%f&right=%f" % (bbox.max_lat, bbox.min_lon, bbox.min_lat, bbox.max_lon))
	except urllib2.HTTPError:
		ui.error(_("JOSM Remote Control command failed."))

def add_obj(obj, ui, server):
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

	# Create a small bounding box with the center.
	bbox = (
			obj.lat + 0.001,
			obj.lon - 0.001,
			obj.lat - 0.001,
			obj.lon + 0.001,
			)

	try:
		josm_remote("load_and_zoom", "top=%f&left=%f&bottom=%f&right=%f" % bbox)
		josm_remote("import", {'url': temp_url})
	except urllib2.HTTPError:
		ui.error(_("JOSM Remote Control command failed."))

def josm_remote(command, params):
	if type(params) is not str:
		params = urllib.urlencode(params)
	url = "http://127.0.0.1:8111/%s?%s" % (command, params)
	print "JOSM Remote Control:", url
	http = urllib2.urlopen(url)
	print http.read()

