#! /usr/bin/python
# Copyright 2011, Trinity College Computing Center
# Written by David Chappell
# Last modified: 19 May 2011

# This is a version of ../../lib/osm_file.py.

import string
import codecs

class OsmObj:
	def merge_osm_tags(self, new_osm_tags):
		self.osm_tags.update(new_osm_tags)

	def osm_tags_as_string(self):
		text = ""
		if self.osm_tags:
			for name, value in self.osm_tags.items():
				if value:
					text += ' <tag k="%s" v="%s"/>\n' % (self.encode(name), self.encode(value))
		return text

	def encode(self, text):
		text = text.replace('&', '&amp;')
		text = text.replace('<', '&lt;')
		text = text.replace('>', '&gt;')
		return text

class OsmNode(OsmObj):
	def __init__(self, id, lat, lon, osm_tags):
		assert type(lat) == float
		assert type(lon) == float
		self.id = id
		self.lat = lat
		self.lon = lon
		self.osm_tags = osm_tags

	def __str__(self):
		text = "<node id='%d' lat='%s' lon='%s'>\n" % (self.id, repr(self.lat), repr(self.lon))
		text += self.osm_tags_as_string()
		text += "</node>\n"
		return text

class OsmWay(OsmObj):
	def __init__(self, id, node_ids, osm_tags):
		self.id = id
		self.node_ids = node_ids
		self.osm_tags = osm_tags

	def __str__(self):
		text = '<way id="%d">\n' % self.id
		for node_id in self.node_ids:
			text += '  <nd ref="%d"/>\n' % node_id
		text += self.osm_tags_as_string()
		text += "</way>\n"
		return text

class OsmWriter:

	def __init__(self, writable_object, creator):
		self.fh = writable_object
		self.creator = creator
		self.next_id = -1			# JOSM uses one counter for both nodes and ways, so must be OK
		self.nodes_by_coords = {}
		self.nodes = {}
		self.ways = []

	def __del__(self):
		self.fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
		self.fh.write('<osm version="0.6" generator="%s">\n' % self.creator)
		for id, node in self.nodes.items():
			self.fh.write(str(node))
		for way in self.ways:
			self.fh.write(str(way))
		self.fh.write("</osm>\n")

	def add_node(self, lat, lon, osm_tags={}):
		coord_key = "%s %s" % (repr(lat), repr(lon))
		id = self.nodes_by_coords.get(coord_key)
		if id:
			self.nodes[id].merge_osm_tags(osm_tags)	
		else:
			id = self.next_id
			self.next_id -= 1
			self.nodes[id] = OsmNode(id, lat, lon, osm_tags)
			self.nodes_by_coords[coord_key] = id
		return id

	def add_way(self, nodes, osm_tags={}):
		id = self.next_id
		self.next_id -= 1
		node_ids = []
		for node in nodes:
			node_ids.append(self.add_node(node[0], node[1]))
		self.ways.append(OsmWay(id, node_ids, osm_tags))

if __name__ == "__main__":
	import sys
	osm = OsmWriter(sys.stdout, "OsmWriter test")
	osm.add_node(42.0, -72.0, {'name':'smith'})
	osm.add_node(42.0, -72.0, {'addr:housenumber':'12'})
	osm.add_way([
		[42.0, -72.0],
		[43.0, -72.0],
		[43.0, -71.0],
		[42.0, -72.0]
		])

