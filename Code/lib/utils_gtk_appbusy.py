# utils_appbusy.py
# Copyright 2012, Trinity College Computing Center
# Last modified: 6 December 2012

import gtk

# When this class is instantiated, the GTK cursor is set to the busy cursor
# and the indicated message is displayed on the status line. When the object
# instance is destroyed, the normal cursor is restored and the status line
# is cleared. The caller should keep a reference to the instance of this
# class in a local variable so that this object will be destroyed 
# automatically when it exits.
#
# The caller can call the error() method to leave a message
# on the status line.
#
class AppBusy(object):
	def __init__(self, window, statusbar, message):
		self.window = window			# toplevel
		self.statusbar = statusbar		# object with set_text() and get_text()
		self.message = message			# message to put on statusbar

		print "BUSY:", message
		self.handle_events()
		self.window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
		self.statusbar.set_text(self.message)
		self.handle_events()

	# Called when the reference to this object goes out of scope
	def __del__(self):
		#print "Busy has gone out of scope."

		# Perform these actions only if the main window still exists.
		# (It will not if the app was closed during the operation
		# on which we are reporting.)
		if self.window.window:

			# Set the cursor back to the default.
			self.window.window.set_cursor(None)

			# If original messages is still there, clear it.
			if self.statusbar.get_text() == self.message: 
				self.statusbar.set_text("")

	# Call this to leave a message after the task is done.
	def error(self, message):
		self.statusbar.set_text(message)
		print "ERROR:", message

	def handle_events(self):
		while gtk.events_pending():
			gtk.main_iteration(False)

