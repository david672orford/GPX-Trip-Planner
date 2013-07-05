# lib/utils_splash.py
# Copyright 2013, Trinity College Computing Center
# Last modified: 14 January 2013

import gtk
import pykarta.misc

# The application objects __init__() method should create an instance of
# this and keep a reference to it in a local variable. When it exists 
# the local variable will go out of scope, the reference count of the 
# instance of this object will go to zero, __del__() will be called,
# and the splash screen will disappear.
class Splash(object):
	def __init__(self, app_obj, image_filename):
		print "Splash:", image_filename
		self.app_obj = app_obj

		# Hook the application's error_dialog() method so that we can
		# make the splash screen disappear before the dialog box appears.
		self.real_error_dialog = self.app_obj.error_dialog
		self.app_obj.error_dialog = pykarta.misc.BoundMethodProxy(self.error_dialog_hook)

		# Create a white window
		self.window = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
		self.window.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("white"))

		# Ask the window manager not to decorate it and to put it in the center
		# of the screen. The way we do this is somewhat redundant because
		# we want to be sure to be understood.
		# FIXME: disabled because Ubuntu Unity loses the WM icon!
		#self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_SPLASHSCREEN)	# enough under GNOME
		self.window.set_position(gtk.WIN_POS_CENTER)						# needed on Win32
		self.window.set_decorated(False)									# needed on Win32
		self.window.set_keep_above(True)

		# Load the image and put it in the white window.
		image = gtk.Image()
		image.set_from_file(image_filename)
		self.window.add(image)

		self.window.show_all()

		while gtk.events_pending():
			gtk.main_iteration(False)

	# This is called when TerritoryEditor.__init__() exits.
	def __del__(self):
		print "Splash: out of scope"
		self.hide()
		self.app_obj.error_dialog = self.real_error_dialog

	def error_dialog_hook(self, title, error_message):
		self.hide()
		self.real_error_dialog(title, error_message)

	def hide(self):
		if self.window:
			print "Splash: hiding"
			self.window.destroy()
			self.window = None


