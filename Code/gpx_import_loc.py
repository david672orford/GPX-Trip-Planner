#! /usr/bin/python
# gpx_import_loc.py
# LOC file import support
# Copyright 2013, 2014, Trinity College
# Last modified: 28 March 2014

def load(filename, datastore):
	import xml.etree.cElementTree as ET
	from gpx_data_gpx import GpxWaypoint

	tree = ET.parse(filename)
	wp_src = tree.getroot().get("src")
	for waypoint in tree.findall("waypoint"):

		wp_coord = waypoint.find("coord")
		wp_name = waypoint.find("name")
		wp_type = waypoint.find("type")
		wp_link = waypoint.find("link")

		point = GpxWaypoint(float(wp_coord.get("lat")), float(wp_coord.get("lon")))
		point.name = wp_name.get("id")
		point.desc = wp_name.text.strip()
		point.type = wp_type.text
		if wp_type.text == "Geocache":
			point.sym = "Geocache"	
		point.link = wp_link.text
		point.src  = wp_src

		datastore.waypoints.append(point)

# Test code
if __name__ == "__main__":
	class DummyDatastore(object):
		pass

	datastore = DummyDatastore()
	datastore.waypoints = []
	load_loc("geocaching.loc", datastore)
	for attr in dir(datastore.waypoints[0]):
		print attr, getattr(datastore.waypoints[0], attr)

