# pykarta/maps/symbols.py
# Copyright 2013, Trinity College
# Last modified: 28 March 2013

import os
import re
import cairo

try:
	import rsvg
except:
    import pykarta.fallback.rsvg as rsvg

#========================================================================
# SVG Map Symbols
#========================================================================

# This class describes a set of MapSymbol objects indexed by their names.
class MapSymbolSet(object):
	def __init__(self):
		self.symbols = {}

	# Load an SVG icon which will later be identified by name.
	# The name and offset (for placement relative to its stated
	# coordinates) are extracted from the filename.
	def add_symbol(self, filename):
		symbol = MapSymbol(filename)
		self.symbols[symbol.name] = symbol

	# Retrieve a member of this symbol set.
	# name--name of prefered symbol
	# default--name of fallback symbol 
	def get_symbol(self, name, default=None):
		if name in self.symbols:
			return self.symbols[name]
		elif default is not None and default in self.symbols:
			return self.symbols[default]
		else:
			return None

	# Get all of the map symbols rendered into pixbufs.
	# This is for controls which allow the user to pick a symbol.
	def get_symbol_pixbufs(self):
		list = []
		for name, symbol in sorted(self.symbols.items()):
			list.append([name, symbol.get_pixbuf()])
		return list

# This class describes a single map symbol loaded from an SVG file.
class MapSymbol(object):
	def __init__(self, filename):
		self.filename = filename
		self.svg = None
		self.pixbuf = None
		self.renderers = {}

		if not os.path.exists(self.filename):
			raise AssertionError("No such file: %s" % self.filename)

		# dir/Pin, Green.0x16.svg
		basename = os.path.basename(filename)
		base, ext = os.path.splitext(basename)
		m = re.search('^(.+)\.(\d+)x(\d+)$', base)
		if m:
			self.name = m.group(1)
			self.anchor = [int(m.group(2)), int(m.group(3))]
		else:
			self.name = base
			self.anchor = None

	# Load the SVG description of the symbol from the file (if it has not
	# been loaded already).
	def get_svg(self):
		if self.svg is None:
			self.svg = rsvg.Handle(self.filename)
			if self.svg is None:
				raise AssertionError("Failed to load SVG file: %s" % filename)
			self.width, self.height = self.svg.get_dimension_data()[:2]
		if self.anchor is None:
			self.anchor = (self.width / 2, self.height / 2)
		return self.svg

	# Get a map symbol rendered as a Gtk Pixbuf which we can use in GTK
	# widgets. Unlike when the symbols are rendered on the map (when they
	# are scaled according to the zoom level) here they are always rendered
	# in their natural size.
	def get_pixbuf(self):
		self.get_svg()
		if self.pixbuf is None:
			self.pixbuf = self.svg.get_pixbuf()
		return self.pixbuf

	# Return an object which can be called on to render this symbol at appropriate scale.
	# This method needs access to the containing map so that it can learn the zoom
	# level and whether this is a print map or a screen map.
	def get_renderer(self, containing_map):
		zoom = containing_map.get_zoom()
		symbol_scale = max(0.50, float(zoom-10) / 5)		# (11-10) / 5 = 0.2, (15-10 / 5 = 1.0, (20-10) / 5 = 4.0
		key = (containing_map.print_mode, symbol_scale)
		if not key in self.renderers:
			if containing_map.print_mode:
				self.renderers[key] = MapSymbolPrintRenderer(self, symbol_scale)
			else:
				self.renderers[key] = MapSymbolScreenRenderer(self, symbol_scale)

		return self.renderers[key]

# Render a map symbol from an SVG file and return an object which 
# encapsulates a Cairo raster image surface and the information
# which we need to place it correctly on the map.
class MapSymbolScreenRenderer(object):
	def __init__(self, symbol, scale):
		svg = symbol.get_svg()
		self.anchor_x, self.anchor_y = map(lambda n: n * scale, symbol.anchor)

		width = int(symbol.width*scale)
		height = int(symbol.height*scale)
		self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
		ctx = cairo.Context(self.surface)
		ctx.scale(scale, scale)
		svg.render_cairo(ctx)

		# For hit detection
		self.bbox_tl_x = 0 - self.anchor_x
		self.bbox_tl_y = 0 - self.anchor_y
		self.bbox_br_x = width - self.anchor_x
		self.bbox_br_y = height - self.anchor_y

		self.label_offset = width * 0.7 - self.anchor_x		# 0.7 is for slight overlap
		self.x_size = width * 1.0

	# Place a copy of the symbol at the indicated position.
	def blit(self, ctx, x, y):
		ctx.set_source_surface(self.surface, int(x - self.anchor_x), int(y - self.anchor_y))
		ctx.paint()

	# Is the given point (relative to the pixel position of the map symbol's
	# stated position) within its bounding box (which takes into account
	# any possible offset)?
	def hit(self, x, y):
		return x >= self.bbox_tl_x and x <= self.bbox_br_x and y >= self.bbox_tl_y and y <= self.bbox_br_y

# Substitute for MaySymbolScreenRenderer() which renders directly from the SVG
# without first creating a pixel surface.
class MapSymbolPrintRenderer(object):
	def __init__(self, symbol, scale):
		self.symbol = symbol
		self.svg = symbol.get_svg()
		self.anchor_x, self.anchor_y = map(lambda n: n * scale, symbol.anchor)
		self.scale = scale
		self.label_offset = symbol.width*scale*0.7 - self.anchor_x
		self.x_size = symbol.width * 1.0

	def blit(self, ctx, x, y):
		ctx.save()
		ctx.translate(x, y)
		ctx.scale(self.scale, self.scale)
		ctx.translate(-self.anchor_x, -self.anchor_y)
		self.svg.render_cairo(ctx)
		ctx.restore()

