# pykarta/maps/layers/mapquest.py
# Mapquest layers
# Copyright 2013, Trinity College
# Last modified: 15 April 2013

import gtk
import urllib
import math
import json

from pykarta.geometry import Point
from pykarta.maps.layers import MapLayer
from pykarta.misc.http import simple_urlopen
from pykarta.maps.image_loaders import surface_from_pixbuf
from pykarta.draw import poi_label

#=============================================================================
# Mapquest live traffic
# See: http://www.mapquestapi.com/traffic/
#
# This is only a proof-of-concept implementation.
# A proper implementation would:
# * download in a separate thread
# * download for a somewhat large area so as not to have to redownload
#   every time the user moved the map
# * automatically redownload every 10 minutes or so
#=============================================================================
class MapTrafficLayer(MapLayer):
	# These are the scales which Mapquest recommends for the
	# indicated mercartor zoom levels.
	scales = {
		10: '433343',
		11: '216671',
		12: '108335',
		13: '54167',
		14: '27083',
		15: '13541',
		16: '6770',
		17: '3385',
		18: '1692',
		}

	# The Mapquest app key for GPX-Trip-Planner
	app_key = "Fmjtd|luub2q68n1,rx=o5-961590"

	incident_symbols = {
		1: 'Construction',
		4: 'Transport Incident',
		}

	def __init__(self):
		MapLayer.__init__(self)
		self.traffic_overlay = None
		self.incidents = None
		self.visible_objs = []

	def do_viewport(self):
		lat, lon, zoom = self.containing_map.get_center_and_zoom()
		bbox = self.containing_map.get_bbox()

		# Download layer which overlays lines on roads.
		int_zoom = min(int(zoom + 0.5), 18)
		self.scale_factor = math.pow(2, zoom) / (1 << int_zoom)
		print "Traffic int_zoom:", int_zoom
		print "Traffic scale_factor:", self.scale_factor
		self.map_height = self.containing_map.height
		self.map_width = self.containing_map.width
		self.image_height = self.map_height / self.scale_factor
		self.image_width = self.map_width / self.scale_factor
		params = {
			'key':self.app_key,
			'projection':'merc',
			'mapLat': str(lat),
			'mapLng': str(lon),
			'mapHeight': str(int(self.image_height)),
			'mapWidth': str(int(self.image_width)),
			'mapScale': self.scales[int_zoom],
			}
		url = "http://www.mapquestapi.com/traffic/v1/flow?%s" % urllib.urlencode(params)
		print "Traffic overlay URL:", url
		response = simple_urlopen(url, {})
		content_length = int(response.getheader("content-length"))
		print "content-length:", content_length
		if content_length > 0:
			data = response.read()
			print "data length:", len(data)
			loader = gtk.gdk.PixbufLoader()
			loader.write(data)
			try:
				loader.close()	# fails due to incomplete GIF
			except:
				pass
			self.traffic_overlay = surface_from_pixbuf(loader.get_pixbuf())
		else:
			self.traffic_overlay = None

		# Download markers which indicate locations of construction or incidents
		params = {
			'key':self.app_key,
			'inFormat':'kvp',
			'boundingBox':"%f,%f,%f,%f" % (bbox.max_lat, bbox.min_lon, bbox.min_lat, bbox.max_lon),
			}
		url = "http://www.mapquestapi.com/traffic/v1/incidents?%s" % urllib.urlencode(params)
		print "Traffic incidents URL:", url
		response = simple_urlopen(url, {})
		self.incidents = json.loads(response.read())
		print json.dumps(self.incidents, indent=4, separators=(',', ': '))

		self.visible_objs = []
		for incident in self.incidents['incidents']:
			x, y = self.containing_map.project_point(Point(incident['lat'], incident['lng']))
			symbol_name = self.incident_symbols.get(incident['type'], "Dot")
			symbol = self.containing_map.symbols.get_symbol(symbol_name)
			renderer = symbol.get_renderer(self.containing_map)
			self.visible_objs.append([x, y, renderer, incident['shortDesc']])

	def do_draw(self, ctx):
		if self.traffic_overlay:
			ctx.translate(self.map_width / 2.0, self.map_height / 2.0)
			ctx.scale(self.scale_factor, self.scale_factor)
			ctx.translate(-(self.image_width / 2.0), -(self.image_height / 2.0))
			ctx.set_source_surface(self.traffic_overlay, 0, 0)
			ctx.paint_with_alpha(0.5)
		for obj in self.visible_objs:
			x, y, renderer, label = obj
			renderer.blit(ctx, x, y)
			poi_label(ctx, x+renderer.label_offset, y, label)

