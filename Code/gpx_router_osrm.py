# gpx_router_mapquest.py
# Copyright 2013, Trinity College
# Last modified: 17 April 2013

import urllib2
import json

from gpx_data_gpx import GpxRoutePoint

class GpxRouter(object):

	url = 'http://router.project-osrm.org/viaroute'

	def flesh_out(self, route):
		print "Route:", route

		locations = []
		for point in route:
			print "  Point:", point.lat, point.lon
			locations.append("loc=%f,%f" % (point.lat, point.lon))

		url = "%s?alt=false&instructions=true&z=18&%s" % (self.url, '&'.join(locations))
		print "URL:", url
		http_resp = urllib2.urlopen(url)
		resp = json.loads(http_resp.read())
		print json.dumps(resp, indent=4, separators=(',', ': '))
		route_geometry = decode_line(resp['route_geometry'])

		while len(route) > 0:
			del route[0]

		for point in route_geometry:
			route.append(GpxRoutePoint(point[0], point[1]))

# From http://seewah.blogspot.com/2009/11/gpolyline-decoding-in-python.html
def decode_line(encoded):

    """Decodes a polyline that was encoded using the Google Maps method.

    See http://code.google.com/apis/maps/documentation/polylinealgorithm.html
    
    This is a straightforward Python port of Mark McClure's JavaScript polyline decoder
    (http://facstaff.unca.edu/mcmcclur/GoogleMaps/EncodePolyline/decode.js)
    and Peter Chng's PHP polyline decode
    (http://unitstep.net/blog/2008/08/02/decoding-google-maps-encoded-polylines-using-php/)
    """

    encoded_len = len(encoded)
    index = 0
    array = []
    lat = 0
    lng = 0

    while index < encoded_len:

        b = 0
        shift = 0
        result = 0

        while True:
            b = ord(encoded[index]) - 63
            index = index + 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break

        dlat = ~(result >> 1) if result & 1 else result >> 1
        lat += dlat

        shift = 0
        result = 0

        while True:
            b = ord(encoded[index]) - 63
            index = index + 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break

        dlng = ~(result >> 1) if result & 1 else result >> 1
        lng += dlng

        array.append((lat * 1e-5, lng * 1e-5))

    return array

if __name__ == "__main__":
    latlngs = decode_line("grkyHhpc@B[[_IYiLiEgj@a@q@yEoAGi@bEyH_@aHj@m@^qAB{@IkHi@cHcAkPSiMJqEj@s@CkFp@sDfB}Ex@iBj@S_AyIkCcUWgAaA_JUyAFk@{D_]~KiLwAeCsHqJmBlAmFuXe@{DcByIZIYiBxBwAc@eCcAl@y@aEdCcBVJpHsEyAeE")
    for latlng in latlngs:
        print str(latlng[0]) + "," + str(latlng[1])

