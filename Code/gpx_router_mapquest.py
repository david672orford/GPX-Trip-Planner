# gpx_router_mapquest.py
# Copyright 2013, Trinity College
# Last modified: 27 June 2013

import json
import urllib2
from gpx_data_gpx import GpxRoutePoint, GpxRouteShapePoint

# This uses Mapquest's router for OSM data.
# See: http://open.mapquestapi.com/directions/
class GpxRouter(object):

	#url = "http://open.mapquestapi.com/directions/v0/optimizedroute?outFormat=json"
	url = "http://open.mapquestapi.com/directions/v1/optimizedroute?outFormat=json"

	def flesh_out(self, route):
		print "Route:", route

		# Collect a list of the waypoints
		locations = []
		for point in route:
			print "  Point:", point.lat, point.lon
			locations.append({'latLng':{'lat': point.lat, 'lng': point.lon}})

		# Construct the query to the routing service
		json_text = json.dumps({
			'locations': locations,
			'options': {
				'shapeFormat': 'raw',
				'generalize': 10,
				},
			}, separators=(',',':'))
		json_text = json_text.replace('"', '')
		print json_text

		# Send the query
		url = "%s&json=%s" % (self.url, json_text)
		print "URL:", url
		http_resp = urllib2.urlopen(url)
		resp = json.loads(http_resp.read())
		#print json.dumps(resp, indent=4, separators=(',', ': '))

		if resp['info']['statuscode'] != 0:
			print "Failed to find route:", resp['info']['messages'][0]

		# Keep just the part which describes the computed route.
		resp = resp['route']

		# This is an array of all of the points in the route: points provided by
		# the user, points added at turns (maneuver start points), and points
		# added in between to smooth the line. The entries at even-numbered indexes
		# are latitudes, each coresponding longitude is one higher.
		shape_points = resp['shape']['shapePoints']

		# This is an index for finding the pair in shapePoints which cooresponds 
		# to a given maneuver (counted from the first maneuver of the first leg).
		shape_indexes = resp['shape']['maneuverIndexes']

		new_route = []
		maneuver_overall_i = 0
		for resp_leg in resp['legs']:		# legs coorespond to our original points
			print " Leg:"
			maneuver_i = 0
			# Step through the maneuvers of this leg, but skip the last one
			# since it is a repetition of the first maneuver of the next leg
			# (or it is the destination point).
			for resp_maneuver in resp_leg['maneuvers'][0:-1]:
				start_point = resp_maneuver['startPoint']
				narrative = resp_maneuver['narrative']
				streets = resp_maneuver['streets']
				print "  Maneuver:", start_point, narrative
				print "    Streets:", streets

				# If first maneuver in leg, use existing point. This point will
				# either be a guide point or a stop.
				if maneuver_i == 0:
					route_point = route[0]
					del route[0]
					# If this is a guide point, snap it to the road and name the source
					# of the new position. Also, set the name if there is none.
					if route_point.type == 'guide':
						route_point.lat = start_point['lat']
						route_point.lon = start_point['lng']
						route_point.src = "Mapquest Open Directions"

				# Otherwise, create new point.
				else:
					route_point = GpxRoutePoint(start_point['lat'], start_point['lng'])
					if len(streets) > 0:
						route_point.name = streets[0]
					else:
						route_point.name = "Maneuver"
					route_point.type = "maneuver"
					route_point.src = "Mapquest Open Directions"

				# Put the written directions in the point's description field.
				route_point.desc = narrative

				# Extract the segment of the route shape which comes after
				# this point and attach it to the point.
				if shape_points:
					shape_start = shape_indexes[maneuver_overall_i] * 2
					try:
						shape_stop = shape_indexes[maneuver_overall_i+1] * 2
					except:
						shape_stop = len(shape_points)
					print "    Shape start:", shape_start
					print "    Shape stop:", shape_stop
					shape_start += 2
					shape_stop -= 2
					route_point.route_shape = []
					while shape_start < shape_stop:
						shape_point = GpxRouteShapePoint(shape_points[shape_start], shape_points[shape_start+1])
						#print "    Shape point:", shape_point
						route_point.route_shape.append(shape_point)
						shape_start += 2

				# This route point is ready.
				new_route.append(route_point)

				maneuver_i += 1
				maneuver_overall_i += 1
			maneuver_overall_i += 1			# make up for skipping of last in each leg

		# End point
		new_route.append(route[0])
		del route[0]

		if len(route) != 0:
			raise AssertionError("%d items left in old route" % len(route))

		# Replace the route
		for point in new_route:
			route.append(point)

		# Set metadata
		route.cmt = "Distance: %.1f miles, Time: %s, Waypoints: %d" % (resp['distance'], resp['formattedTime'], len(route))

# end of file

