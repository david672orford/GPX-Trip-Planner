#! /usr/bin/python3
# Copyright 2013--2023, Trinity College

import sys
import os
import xml.sax
import xml.sax.saxutils
import re
import gzip

import pykarta.geometry

class GpxTrk(object):
	def __init__(self):
		self.segments = []
		self.name = ""
	def append(self, segment):
		self.segments.append(segment)
	def __iter__(self):
		for i in self.segments:
			yield i
	def __getitem__(self, i):
		return self.segments[i]
	def write(self, writer):
		writer.characters(" ")
		writer.startElementNL('trk', {})
		writer.characters("  ")
		writer.simpleTextElement('name', self.name)
		for segment in self.segments:
			segment.write(writer)
		writer.characters(" ")
		writer.endElementNL('trk')
	def get_bbox(self):
		bbox = pykarta.geometry.BoundingBox()
		for trkseg in self.segments:
			for trkpt in trkseg:
				bbox.add_point(pykarta.geometry.Point(trkpt.lat, trkpt.lon))
		return bbox

class GpxTrkseg(object):
	def __init__(self):
		self.points = []
	def append(self, point):
		self.points.append(point)
	def __iter__(self):
		for i in self.points:
			yield i
	def __getitem__(self, i):
		return self.points[i]
	def write(self, writer):
		writer.characters(" ")
		writer.startElementNL('trkseg', {})
		for point in self.points:
			point.write(writer)
		writer.endElementNL('trkseg')

class GpxTrkpt(object):
	__slots__ = ['lat', 'lon', 'ele', 'time']
	def __init__(self, lat, lon):
		self.lat = lat
		self.lon = lon
		self.ele = None
		self.time = None
	def write(self, writer):
		writer.characters("  ")
		writer.startElementNL('trkpt', {'lat': repr(self.lat), 'lon': repr(self.lon)})
		if self.ele != None:
			writer.characters("   ")
			writer.simpleTextElement('ele', self.ele)		# was not converted to float
		if self.time != None:
			writer.characters("   ")
			writer.simpleTextElement('time', self.time)
		writer.characters("  ")
		writer.endElementNL('trkpt')

class GpxReader(xml.sax.handler.ContentHandler):
	def __init__(self, fh):
		self.fh = fh

		self.trks = []
		self.trk = None
		self.trkseg = None
		self.trkpt = None
		self.name = None
		self.value = None

		self.parser = xml.sax.make_parser()
		self.parser.setContentHandler(self)
		self.parser.parse(fh)

	def startElement(self, name, attrs):
		if name == 'trk':
			self.trk = GpxTrk()
			self.trks.append(self.trk)
		elif name == 'trkseg':
			assert self.trk != None
			self.trkseg = GpxTrkseg()
			self.trk.append(self.trkseg)
		elif name == 'trkpt':
			assert self.trkseg != None
			self.trkpt = GpxTrkpt(float(attrs.get('lat')), float(attrs.get('lon')))
			self.trkseg.append(self.trkpt)
		elif self.trkpt != None and (name == 'ele' or name == 'time'):
			self.name = name
			self.value = ""

	def endElement(self, name):
		if name == 'trk':
			self.trk = None
		elif name == 'trkseg':
			self.trkseg = None
		elif name == 'trkpt':
			self.trkpt = None
		elif name == self.name:
			setattr(self.trkpt, self.name, self.value)
			self.name = None
			self.value = None

	def characters(self, text):
		if self.trkpt != None and self.name != None:
			self.value += text

class GpxWriter(xml.sax.saxutils.XMLGenerator):
	def __init__(self, fh):
		fh.write("<?xml version='1.0' encoding='UTF-8'?>\n")
		xml.sax.saxutils.XMLGenerator.__init__(self, fh)
		self.startElementNL("gpx", {
			'version': "1.1",
			'creator': "GPX Splitter",
			'xmlns': "http://www.topografix.com/GPX/1/1",
			})

	def __del__(self):
		self.endElementNL("gpx")

	def startElementNL(self, type, attrs={}):
		self.startElement(type, attrs)
		self.characters("\n")

	def endElementNL(self, type):
		self.endElement(type)
		self.characters("\n")

	def simpleTextElement(self, type, text):
		self.startElement(type, {})
		self.characters(text)
		self.endElementNL(type)

for filename in sys.argv[1:]:
	print(filename)
	#fh = open(filename, "r")
	fh = gzip.open(filename, "r")

	gpx = GpxReader(fh)

	for trk in gpx.trks:

		datetime = trk[0][0].time
		print(datetime)
		m = re.match('(\d\d\d\d)-(\d\d)-(\d\d)T', datetime)
		assert m
		datetime_code = m.group(1) + m.group(2) + m.group(3)
		trk.name = datetime_code

		bbox = trk.get_bbox()
		bbox_width = (bbox.max_lon - bbox.min_lon)
		bbox_height = (bbox.max_lat - bbox.min_lat)

		if bbox_height > 0.0005 or bbox_width > 0.0005:
			prefix = "track"
		else:
			prefix = "noise"

		filename = "Processed_Tracks/%s_%s_%f,%f,%f,%f.gpx.gz" % (
			prefix,
			datetime_code,
			bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat,
			)
		print("Writing to %s..." % filename)
		ofh = gzip.open(filename, "w")
		writer = GpxWriter(ofh)
		writer.startElementNL('metadata', {})
		writer.startElement('bounds', {
			'minlon': repr(bbox.min_lon),
			'minlat': repr(bbox.min_lat),
			'maxlon': repr(bbox.max_lon),
			'maxlat': repr(bbox.max_lat),
			})
		writer.endElement('bounds')
		writer.endElementNL('metadata')
		trk.write(writer)
