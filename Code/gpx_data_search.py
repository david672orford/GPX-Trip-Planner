#! /usr/bin/python
# gpx_data_search.py
# Copyright 2013, Trinity College
# Last modified: 29 March 2013

import gtk
import gobject
import urllib2
import xml.etree.cElementTree as ET
import json

from gpx_data_gpx import GpxPoint
import pykarta.geometry

base_url = "http://open.mapquestapi.com/nominatim/v1/search?format=xml&addressdetails=1&polygon=1&limit=100"

# One of these for each search match. It expands GpxPoint to include
# a zoom level at which to display it.
class SearchMatch(GpxPoint):
	def __init__(self, *args):
		GpxPoint.__init__(self, *args)
		self.zoom = None
		self.polygonpoints = []

# This object wraps a gtk.Liststore which contains the list of 
# search matches.
class SearchMatches(object):
	def __init__(self, map_obj):
		self.datastore = gtk.ListStore(gobject.TYPE_PYOBJECT, gobject.TYPE_STRING, gtk.gdk.Pixbuf, gobject.TYPE_STRING)
		self.map_obj = map_obj

		# This clients of this datastore
		self._clients = {}

		self.datastore.connect("row-deleted", self.row_cb)
		self.datastore.connect("row-changed", self.row_cb)

	def row_cb(self, treemodel, path, iter=None):
		if 'map_layer' in self._clients:
			self._clients['map_layer'].set_stale()

	def add_client(self, client_name, client_obj):
		self._clients[client_name] = client_obj

	def clear(self):
		self.select(None, "clear()")
		self.datastore.clear()

	def append(self, match):
		self.datastore.append([match, len(self.datastore)+1, self.map_obj.symbols.get_symbol(match.sym, None).get_pixbuf(), match.desc])

	def __len__(self):
		return len(self.datastore)

	def __getitem__(self, index):
		return self.datastore[index][0]

	def select(self, path, source):
		print "%s: %s selected %s" % ("SearchMatches", source, path)
		for client_name, client_obj in self._clients.items():
			if client_name != source:
				client_obj.on_select(path, source, client_name)

def search_nominatim(search_terms, scope=None, bbox=None):
	print "Search for:", search_terms

	if scope == "scope_within":
		#scope_params = "&viewbox=%s,%s,%s,%s&bounded=1&polygon=1" % (left, top, right, bottom)
		scope_params = "&viewbox=%s,%s,%s,%s&bounded=1&polygon=1" % (bbox.min_lon, bbox.max_lat, bbox.max_lon, bbox.min_lat)
	elif scope == "scope_usa":
		scope_params = "&countrycodes=US"
	else:
		scope_params = ""

	url = "%s%s&q=%s" % (base_url, scope_params, search_terms.replace(' ', '+'))
	print "URL:", url
	http_resp = urllib2.urlopen(url)
	resp_text = unicode(http_resp.read())
	#print resp_text
	tree = ET.XML(resp_text)

	answer = []
	for match in tree.findall("place"):

		match_obj = SearchMatch(float(match.get("lat")), float(match.get("lon")))
		match_obj.src = "Nominatim"

		match_class = match.get("class")
		match_type = match.get("type")
		print "  Candidate: %s" % match.get("display_name")
		print "    Coordinates: (%s, %s)" % (match_obj.lat, match_obj.lon)
		print "    Class: %s" % match_class
		print "    Type: %s" % match_type
		print "    Icon: %s" % match.get("icon")

		if match_class == "boundary":
			match_obj.polygonpoints = map(lambda i: pykarta.geometry.Point(float(i[1]), float(i[0])), json.loads(match.get('polygonpoints')))

		# Format the name of the place and its address
		line1 = ""
		line2 = []
		line3 = ""
		match_elements = list(match)
		if match_class != "place" and (match_class != "boundary" or match_type != "administrative"):
			while(len(match_elements)) > 0:
				i = match_elements.pop(0)
				print "    line1: %s: %s" % (i.tag, i.text)
				if i.tag == "house_number":
					line1 += ("\n%s " % i.text)
				elif i.tag == "road":
					line1 += ("%s\n" % i.text)
					break
				elif i.tag == match_type:
					line1 += "\n%s (%s: %s)\n" % (i.text, match_class, match_type)
				else:
					match_elements.insert(0, i)		# put it back
					break
			line1 = line1.replace("\n\n", "\n")
			line1 = line1.strip()
		while(len(match_elements)) > 0:
			i = match_elements.pop(0)
			print "    line2: %s: %s" % (i.tag, i.text)
			if i.tag == "county":
				if "County" in i.text.split(" "):
					line2.append(i.text)
				else:
					line2.append("%s [County]" % i.text)
			elif i.tag == "country":
				line3 = i.text
				break
			else:
				line2.append(i.text)
		print "  line1:", line1
		print "  line2:", line2
		print "  line3:", line3
		if line1 != "":
			match_obj.name = line1
			line1 += "\n"
		elif match_class == "place" and match_type == "house" and len(line2) >= 2:
			match_obj.name = " ".join(line2[0:2])
		elif len(line2) >= 1:
			match_obj.name = line2[0]
		match_obj.desc = "%s %s\n" % (match_class, match_type) + line1 + (", ".join(line2)) + "\n" + line3

		# Zoom level depends on object type
		if match_class == "place" and match_type != "house" or match_class == "boundary" and match_type == "administrative":
			match_obj.zoom = 12
		else:
			match_obj.zoom = 14

		# Symbol depends on the object type
		match_obj.sym = "Flag, Blue"

		answer.append(match_obj)

	return answer

if __name__ == "__main__":
	import sys
	answer = freeform_search(sys.argv[1])
	for i in answer:
		print i

