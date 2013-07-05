# pykarta/maps/projection.py

import math

# Convert latitude and longitude to tile coordinates. The whole part of the
# x and y coordinates indicates the tile number. The fractional part
# indicates the position within the tile.
def project_to_tilespace(lat, lon, zoom):
	lat_rad = math.radians(lat)
	n = 2.0 ** zoom
	xtile = (lon + 180.0) / 360.0 * n
	ytile = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n
	return (xtile, ytile)

# Converts tile coordinates back to latitude and longitude
def unproject_from_tilespace(xtile, ytile, zoom):
	n = 2.0 ** zoom
	lon = xtile / n * 360.0 - 180.0
	lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ytile / n))))
	return (lat, lon)

