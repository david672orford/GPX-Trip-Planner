# format_geojson_writer.py
# Copyright 2011, David Chappell
# Last modified: 18 November 2011

import json

class GeojsonWriter:
	def __init__(self):
		self.features = []

	def save(self, filename):
		f = open(filename, 'w')
		self.write(f)
		f.close()

	def save_js(self, filename, varname):
		f = open(filename, 'w')
		f.write("var %s = " % varname)
		self.write(f)
		f.write(";\n")
		f.close()

	def write(self, fh):
		json.dump(
			{
			'type': "FeatureCollection",
			'features': self.features,
			}, fh, separators=(',',':'));

	def __str__(self):
		return json.dumps(
			{
			'type': "FeatureCollection",
			'features': self.features,
			}, separators=(',',':'));

	def add_point(self, lat, lon, properties={}):
		self.features.append(
			{
			'type': "Feature",
			'geometry': {
				'type': "Point",
				'coordinates': [lon, lat],
				},
			'properties': properties,
			});

	def add_polygon(self, vertexes, properties={}):
		self.features.append(
			{
			'type': "Feature",
			'geometry': {
				'type': "Polygon",
				'coordinates': [map(lambda i: [i[1], i[0]], vertexes)],
				},
			'properties': properties,
			});

	def add_linestring(self, vertexes, properties={}):
		self.features.append(
			{
			'type': "Feature",
			'geometry': {
				'type': "LineString",
				'coordinates': map(lambda i: [i[1], i[0]], vertexes),
				},
			'properties': properties,
			});

