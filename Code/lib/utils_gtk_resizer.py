# Code/lib/utils_gtk_resizer.py
# Copyright 2012, Trinity College Computing Center
# Last modified: 10 December 2012

import gtk

class Resizer(object):
	def __init__(self, vbox):
		self.vbox = vbox

		sep = gtk.HSeparator()
		vbox.pack_start(sep, False, False)
		sep.show()

		resizer = gtk.EventBox()
		label = gtk.Label("------------------------------------------------------------------------")
		label.set_size_request(-1, 10)
		resizer.add(label)
		vbox.pack_start(resizer, False, False)
		resizer.connect('realize', lambda widget: widget.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.DOUBLE_ARROW)))
		resizer.show_all()

		self.resize_start_y = None
		self.resize_start_height = None
		self.resize_original_height = None

		resizer.connect('button-press-event', self.resizer_start)
		resizer.connect('button-release-event', self.resizer_stop)
		resizer.connect('motion-notify-event', self.resizer_drag)
		resizer.set_events(gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK)

	def resizer_start(self, widget, event):
		#print "Resize start"
		x, y = widget.translate_coordinates(self.vbox, int(event.x), int(event.y))
		self.resize_start_y = y
		self.resize_start_height = self.vbox.get_allocation().height
		if self.resize_original_height == None:
			self.resize_original_height = self.resize_start_height

	def resizer_stop(self, widget, event):
		#print "Resize end"
		self.resize_start_y = None

	def resizer_drag(self, widget, event):
		#print "Resize drag"
		if self.resize_start_y != None:
			x, y = widget.translate_coordinates(self.vbox, int(event.x), int(event.y))
			change = y - self.resize_start_y
			new_height = self.resize_start_height + change
			#print "new_height:", new_height
			if new_height >= self.resize_original_height:
				self.vbox.set_size_request(-1, new_height)

