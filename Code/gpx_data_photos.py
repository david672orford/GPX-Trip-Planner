#=============================================================================
# gpx_data_photos.py
# Copyright 2013, Trinity College
# Last modified: 11 April 2013
#=============================================================================

import gobject
import gtk
import glob
import os

import EXIF
from gpx_data_gpx import GpxPoint

class GpxPhotos(object):
	def __init__(self):
		self.datastore = gtk.ListStore(gobject.TYPE_PYOBJECT)
		self._clients = {}

	def add_photo(self, filename):
		print " %s" % filename,
		photo = GpxPhoto(filename)
		if photo.lat is not None:
			print "(%f, %f)" % (photo.lat, photo.lon)
			self.datastore.append([photo])
		else:
			print "no coordinates"

	def add_client(self, client_name, client_obj):
		self._clients[client_name] = client_obj

	def select(self, path, source):
		for client_name, client_obj in self._clients.items():
			if client_name != source:
				client_obj.on_select(path, source, client_name)

	def __getitem__(self, path):
		return self.datastore[path][0]

	def touch(self, path):
		print "Modification of photos not implemented"

class GpxPhoto(GpxPoint):
	def __init__(self, filename):
		lat, lon = get_coords(filename)
		GpxPoint.__init__(self, lat, lon)
		self.name = os.path.basename(filename)
		self.sym = "Camera"
		self.filename = filename

# See:
# http://www.cipa.jp/english/hyoujunka/kikaku/pdf/DC-008-2010_E.pdf
# http://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/GPS.html
def get_coords(filename):
	f = open(filename, "rb")
	tags = EXIF.process_file(f)

	# GPS GPSAltitudeRef=0
	# GPS GPSLatitudeRef=N
	# GPS GPSMapDatum=WGS-84
	# GPS GPSVersionID=[2, 0, 0, 0]
	# GPS GPSTimeStamp=[19, 46, 19]
	# GPS GPSDate=2009:12:06
	# GPS GPSLatitude=[42, 7, 2511/100]
	# GPS GPSLongitude=[72, 48, 401/25]
	# GPS GPSLongitudeRef=W
	# GPS GPSAltitude=136053/2000
	if True:
		for name, value in tags.items():
			if name.split(" ")[0] == "GPS":
				print "    %s=%s" % (name, value)

	try:
		return (decimal_degrees(tags, "Latitude", "S"), decimal_degrees(tags, "Longitude", "W"))
	except KeyError:
		return (None, None)

def decimal_degrees(tags, dimension, negative_ref):
	number_tag = tags['GPS GPS%s' % dimension]
	ref_tag = tags['GPS GPS%sRef' % dimension]
	degrees, minutes, seconds = number_tag.values
	decimal_degrees = degrees.num/degrees.den + minutes.num/minutes.den/60.0 + seconds.num/seconds.den/3600.0
	if ref_tag.values == negative_ref:
		decimal_degrees *= -1.0
	return decimal_degrees


