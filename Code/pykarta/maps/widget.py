#=============================================================================
# pykarta/maps/widget.py
# Copyright 2013, Trinity College
# Last modified: 25 April 2013
#=============================================================================

import gtk
import math
import cairo
import copy
import time

import lib.utils_i18n

from pykarta.maps import MapBase, MapCairo, MapFeedback
from pykarta.maps.layers import MapTileLayerHTTP, MapLayerSVG

#=============================================================================
# Gtk Widget
#=============================================================================

class MapWidget(gtk.DrawingArea, MapBase):

	lazy_tiles = True

	def __init__(self, **kwargs):
		gtk.DrawingArea.__init__(self)
		MapBase.__init__(self, **kwargs)

		self.coordinates_cb = None
		self.map_drag_start = None
		self.drag_offset = None

		self.connect('expose-event', self.expose_event)
		self.connect('button-press-event', self.button_press_event)
		self.connect('button-release-event', self.button_release_event)
		self.connect('motion-notify-event', self.motion_notify_event)
		self.connect('leave-notify-event', self.leave_notify_event)
		self.connect('scroll-event', self.scroll_event_cb)
		self.set_events(gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.LEAVE_NOTIFY_MASK)
		self.connect("key_press_event", self.key_press_event)
		self.set_flags(gtk.CAN_FOCUS)
		self.connect('configure-event', self.configure_event)

	# See http://www.pygtk.org/articles/cairo-pygtk-widgets/cairo-pygtk-widgets.htm
	def expose_event(self, widget, event):
		#print "expose_event()"
		ctx = self.window.cairo_create()
		ctx.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
		ctx.clip()

		if self.updated_viewport:
			self.drag_offset = [0, 0]
			self.feedback.debug(1, "Projecting layers:")
			for layer in self.layers_ordered:
				start_time = time.time()
				layer.do_viewport()
				self.elapsed(layer.name, start_time)
				layer.stale = False
			for layer in self.layers_osd:
				start_time = time.time()
				layer.do_viewport()
				self.elapsed(layer.name, start_time)
			self.updated_viewport = False

		# Possibly rotate 90 degrees
		if self.rotate:
			ctx.rotate(math.pi / -2.0)
			ctx.translate(-self.width, 0)	

		# Translate coordinate space to compensate for dragging
		# which may be in progress and paint the layers.			
		ctx.save()
		ctx.translate(self.drag_offset[0], self.drag_offset[1])

		self.feedback.debug(1, "Drawing layers:")
		for layer in self.layers_ordered:
			if layer.stale and not self.map_drag_start:		# if layer is dirty and we are not dragging right now,
				start_time = time.time()
				layer.do_viewport()
				self.elapsed("%s (reproject)" % layer.name, start_time)
				layer.stale = False
			ctx.save()
			start_time = time.time()
			layer.do_draw(ctx)
			self.elapsed(layer.name, start_time)
			ctx.restore()

		ctx.restore()

		for layer in self.layers_osd:
			if layer.stale and not self.map_drag_start:
				layer.do_viewport()
				layer.stale = False
			ctx.save()
			layer.do_draw(ctx)
			ctx.restore()

		return False

	def elapsed(self, opname, start_time):
		stop_time = time.time()
		elapsed_time = int((stop_time - start_time) * 1000 + 0.5)
		if elapsed_time > 0:
			self.feedback.debug(1, " %s: %d ms" % (opname, elapsed_time))

	def key_press_event(self, widget, event):
		keyname = gtk.gdk.keyval_name(event.keyval)
		print "Map: key %s (%d) was pressed" % (keyname, event.keyval)
		if keyname == "Up":
			self.scroll(0, -5)
		elif keyname == "Down":
			self.scroll(0, 5)
		elif keyname == "Left":
			self.scroll(-5, 0)
		elif keyname == "Right":
			self.scroll(5, 0)
		elif keyname == "KP_Add":
			self.zoom_in()
		elif keyname == "KP_Subtract":
			self.zoom_out()
		return True		# don't pass on

	# Mouse wheel zooming
	def scroll_event_cb(self, widget, gdkevent):
		#print "Event:", gdkevent.x, gdkevent.y, gdkevent.direction
		#print "position:", self.get_center_and_zoom()
		zoom = self.get_zoom()
		zoom_step_factor = math.pow(2, self.zoom_step)
		center_x = (self.width / 2)
		center_y = (self.height / 2)
		distance_x = (gdkevent.x - center_x)
		distance_y = (gdkevent.y - center_y)
		# Zoom in: new center is between existing center and mouse pointer
		if gdkevent.direction == gtk.gdk.SCROLL_UP:
			new_center_x = gdkevent.x - (distance_x / zoom_step_factor)
			new_center_y = gdkevent.y - (distance_y / zoom_step_factor)
			lat, lon = self.unproject_point(new_center_x, new_center_y)
			if self.zoom_in() != zoom:
				self.set_center(lat, lon)
			return True
		# Zoom out: new center is beyond existing center as seen from mouse pointer
		elif gdkevent.direction == gtk.gdk.SCROLL_DOWN:
			new_center_x = gdkevent.x - (distance_x * zoom_step_factor)
			new_center_y = gdkevent.y - (distance_y * zoom_step_factor)
			#print "new center:", new_center_x, new_center_y
			lat, lon = self.unproject_point(new_center_x, new_center_y)
			if self.zoom_out() != zoom:
				self.set_center(lat, lon)
			return True
		return False

	# Mouse down event on map
	def button_press_event(self, widget, gdkevent):
		#print "Map: button %d down (%s) at (%d, %d)" % (gdkevent.button, str(gdkevent.type), gdkevent.x, gdkevent.y)

		# Click on map gives it focus so that user can scroll it and zoom using the keyboard.
		self.grab_focus()

		# Pass event down to layers
		for layer in reversed(self.layers_ordered):
			if layer.on_button_press(gdkevent):
				return True

		# Since not handled above, must be for base layer. Keep track of dragging
		# so that we can translate the drawing context to compensate.
		if gdkevent.type == gtk.gdk.BUTTON_PRESS and gdkevent.button == 1:
			self.map_drag_start = [gdkevent.x, gdkevent.y]

		return True

	# Mouse button released over map
	def button_release_event(self, widget, gdkevent):
		#print "Map: button %d up at (%d, %d)" % (gdkevent.button, gdkevent.x, gdkevent.y)

		# Dragging done?
		if self.map_drag_start:
			self._viewport_changed()
			self.scroll(-self.drag_offset[0], -self.drag_offset[1])
			self.map_drag_start = None

		# Pass event down to layers
		for layer in reversed(self.layers_ordered):
			if layer.on_button_release(gdkevent):
				return True

		return True

	# Mouse pointer moved over map
	def motion_notify_event(self, widget, gdkevent):
		#print "Map: mouse pointer at (%d, %d) %s" % (gdkevent.x, gdkevent.y, str(gdkevent.type))

		if self.map_drag_start:
			self.drag_offset = [gdkevent.x - self.map_drag_start[0], gdkevent.y - self.map_drag_start[1]]
			self.queue_draw()

		if self.coordinates_cb:
			self.coordinates_cb(self.unproject_point(gdkevent.x, gdkevent.y))

		for layer in reversed(self.layers_ordered):
			if layer.on_motion(gdkevent):
				return True

		return False

	# Move pointer has left the map.
	def leave_notify_event(self, widget, gdkevent):
		#print "Map: mouse pointer left"
		if self.coordinates_cb:
			self.coordinates_cb(None)

	# Window size or position has changed
	def configure_event(self, widget, event):
		self.set_size(event.width, event.height)
	
	#====================================================================
	# Public methods
	#====================================================================

	# Specify a function which will be called repeatedly as the mouse
	# pointer moves over the map. It will receive a (lat, lon) tuple
	# or None (if the mouse pointer moves out of the map).
	def set_coordinates_cb(self, function):
		self.coordinates_cb = function

	# Set the mouse cursor shape (over the map).
	def set_cursor(self, cursor):
		self.window.set_cursor(cursor)

	def queue_draw(self):
		gtk.DrawingArea.queue_draw(self)

	def precache_tiles(self, main_window=None, max_zoom=16):
		progress = MapPrintProgress(main_window, title=_("Tile Download Progress"))
		for layer in self.layers_ordered:
			if isinstance(layer, MapTileLayerHTTP):
				print layer.tileset.key
				layer.precache_tiles(progress, max_zoom)
		progress.done()

	def reload_tiles(self):
		for layer in self.layers_ordered:
			if isinstance(layer, MapTileLayerHTTP):
				print layer.tileset.key
				layer.reload_tiles()
		self.queue_draw()

#=============================================================================
# Gtk Printing
#=============================================================================
class MapPrint(MapCairo):
	def __init__(self, map_widget, landscape=None, margin=18, main_window=None):
		if not isinstance(map_widget, MapWidget):
			raise TypeError
		if landscape is None:
			self.landscape = map_widget.allocation.width > map_widget.allocation.height
		else:
			self.landscape = landscape
		self.margin = margin
		self.main_window = main_window
		self.map_failure = None

		# Initialize parent class without a tile layer
		MapCairo.__init__(
			self,
			tile_source=None,
			tile_cache_basedir=map_widget.tile_cache_basedir,
			feedback=MapPrintProgress(main_window)
			)

		# Load the same map symbols as the map widget has
		self.symbols = map_widget.symbols

		# Same base layers
		for layer in map_widget.layers_ordered:
			print " %s" % layer.name
			if layer.name == "osm-default":
				layer = MapLayerSVG("osm-default-svg")
			else:
				layer = copy.copy(layer)
			self.add_layer(layer.name, layer)
		self.base_layer_keys = map_widget.base_layer_keys

		# Same OSD layers
		for layer in map_widget.layers_osd:
			layer = copy.copy(layer)
			self.add_osd_layer(layer)

		# Same position and zoom level
		self.set_center_and_zoom(*(map_widget.get_center_and_zoom()))

	# Call this from File->Print
	def do_print(self):
		print_op = gtk.PrintOperation()

		# Page size and orientation
		page_setup = gtk.PageSetup()
		page_setup.set_paper_size_and_default_margins(gtk.PaperSize(gtk.PAPER_NAME_LETTER))
		page_setup.set_orientation(gtk.PAGE_ORIENTATION_LANDSCAPE if self.landscape else gtk.PAGE_ORIENTATION_PORTRAIT)
		print_op.set_default_page_setup(page_setup)

		#if self.print_settings != None:
		#	print_op.set_print_settings(self.print_settings)

		print_op.set_show_progress(False)	# appears late
		print_op.set_use_full_page(True)
		print_op.set_embed_page_setup(True)
		print_op.connect('draw_page', self.draw_page)

		print_op.set_n_pages(1)
		result = print_op.run(gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG, self.main_window)

		self.feedback.done()

		print "Printing result:", result
		if self.map_failure:
			return self.map_failure
		elif result == gtk.PRINT_OPERATION_RESULT_ERROR:
			return print_op.get_error()
		#elif result == gtk.PRINT_OPERATION_RESULT_APPLY:
		#	self.print_settings = print_op.get_print_settings()
		#	return None
		else:
			return None

	# Called as gtk.PrintOperation's draw-page handler
	def draw_page(self, print_op, print_ctx, page_number):
		ctx = print_ctx.get_cairo_context()
		width = print_ctx.get_width()
		height = print_ctx.get_height()

		ctx.translate(self.margin, self.margin)
		width -= (2*self.margin)
		height -= (2*self.margin)
		self.set_size(width, height)

		try:
			self.draw_map(ctx)
		except Exception as e:
			print "Printing failed:"
			import traceback
			traceback.print_exc()
			print_op.cancel()
			self.map_failure = str(e)

		# Draw line around map
		ctx.rectangle(0, 0, width, height)
		ctx.set_line_width(1)
		ctx.set_source_rgb(0.0, 0.0, 0.0)
		ctx.stroke()

# Override the progress() method of MapFeedback so as
# to display a progress dialog.
class MapPrintProgress(MapFeedback):
	def __init__(self, main_window, title=_("Printing Progress")):
		MapFeedback.__init__(self)

		self.canceled = False
		self.shown = False

		self.dialog = gtk.Dialog(
			title=title,
			parent=main_window,
			flags=(gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT),
			buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
			)
		self.dialog.connect("response", self.response_cb)
		self.dialog.set_default_size(400, -1)

		vbox = self.dialog.get_content_area()

		self.message = gtk.Label("")
		vbox.pack_start(self.message)
		self.message.show()

		self.countdown_message = gtk.Label("")
		vbox.pack_start(self.countdown_message)
		self.countdown_message.show()

		self.bar = gtk.ProgressBar()
		vbox.pack_start(self.bar)
		self.bar.show()

	def response_cb(self, widget, response_id):
		print "*** cancel pressed ***"
		self.canceled = True

	def progress(self, x, y, message):
		if self.canceled:
			self.dialog.hide()
			raise KeyboardInterrupt
		if x is not None:
			fraction = float(x) / float(y)
			self.bar.set_fraction(fraction)
			self.bar.set_text("%d%%" % int(fraction * 100.0 + 0.5))
		if message is not None:
			self.message.set_text(message)
			self.countdown_message.set_text("")
		if not self.shown:
			self.dialog.show()
			self.shown = True
		while gtk.events_pending():
			gtk.main_iteration(False)

	def error(self, message):
		self.message.set_text(message)
		self.countdown_message.set_text("")
		while gtk.events_pending():
			gtk.main_iteration(False)

	def countdown(self, message):
		self.countdown_message.set_text(message)
		while gtk.events_pending():
			gtk.main_iteration(False)

	def done(self):
		if self.shown:
			self.dialog.hide()
			self.shown = False

