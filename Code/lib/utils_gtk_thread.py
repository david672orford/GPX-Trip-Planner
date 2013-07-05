# utils_thread.py
# Copyright 2012, Trinity College Computing Center
# Last modified: 17 December 2012

import thread
import gobject

# Safely call functions in the Gtk+ thread and receive their return values.
class GtkCallWrapper(object):
	def __init__(self):
		self.lock = thread.allocate_lock()

	# Run the specified lambda function in the Gtk thread.
	def call(self, function):
		self.function = function
		self.lock.acquire()				# on behalf of Gtk thread
		gobject.idle_add(self.in_gtk)
		self.lock.acquire()				# wait for Gtk thread to release
		self.lock.release()
		return self.result

	# This is run in the Gtk thread
	def in_gtk(self):
		self.result = self.function()
		self.lock.release()


