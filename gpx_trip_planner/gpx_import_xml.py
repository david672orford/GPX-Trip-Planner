#! /usr/bin/python
# gpx_import_xml.py
# XML file import support
# Copyright 2013, 2014, Trinity College
# Last modified: 28 March 2014

def load(filename, datastore):
	import xml.etree.cElementTree as ET
	from gpx_data_gpx import GpxWaypoint

	tree = ET.parse(filename)

	for travelplaza in tree.findall("travelplaza"):
		point = GpxWaypoint(float(travelplaza.get("latitude")), float(travelplaza.get("longitude")))
		point.name = travelplaza.get("title")
		point.desc = "%s %s %s" % (
			travelplaza.get("route"),
			travelplaza.get("direction"),
			travelplaza.get("location")
			)
		point.sym = "Restroom"
		datastore.waypoints.append(point)

