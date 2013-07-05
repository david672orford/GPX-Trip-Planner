# lib/utils_gtk_entry.py
# Copyright 2013, Trinity College
# Last modified: 21 February 2013

import gtk

# Pass gtk.Entry widgets through this function because some of them
# are actually gtk.TextView widgets.
def text_entry_wrapper(widget):
	if widget.__class__ == gtk.TextView:
		return TextEntryWrapper(widget)
	elif widget.__class__ == gtk.ComboBoxEntry:
		return ComboBoxEntryWrapper(widget)
	else:
		return widget

# Make a gtk.TextView widget act more or less like a gtk.Entry widget.
class TextEntryWrapper(object):
	def __init__(self, widget):
		self.buffer = gtk.TextBuffer()
		widget.set_buffer(self.buffer)
		self.changed_cb = None
	def get_text(self):
		return self.buffer.get_text(self.buffer.get_start_iter(), self.buffer.get_end_iter())
	def set_text(self, text):
		self.buffer.set_text(text)
	def get_editable(self):
		return True
	def connect(self, signal, handler, data):
		assert signal == "changed"
		self.changed_cb = handler
		self.buffer.connect(signal, self.springboard_changed_cb, data)
	def springboard_changed_cb(self, textbuffer, data):
		self.changed_cb(self, data)

class ComboBoxEntryWrapper(object):
	def __init__(self, widget):
		self.widget = widget
	def get_text(self):
		return self.widget.child.get_text()
	def set_text(self, text):
		self.widget.child.set_text(text)
	def get_editable(self):
		return True
	def connect(self, *args):
		self.widget.child.connect(*args)

