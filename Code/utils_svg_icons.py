# utils_svg_icons.py

import os, sys

try:
	import rsvg
except:
    import pykarta.fallback.rsvg as rsvg

def load_icon_pixbuf(filename):
	filename = os.path.join(sys.path[0], "images", filename)
	svg = rsvg.Handle(filename)
	if not svg:
		raise AssertionError("Failed to load SVG file: %s" % filename)
	return svg.get_pixbuf()
