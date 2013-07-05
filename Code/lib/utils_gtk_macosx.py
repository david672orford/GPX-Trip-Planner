# utils_gtk_macosx.py

import sys

# See:
# * http://gtk-osx.sourceforge.net/ige-mac-integration/GtkOSXApplication.html
# * http://nullege.com/codes/show/src%40g%40r%40gramps-HEAD%40trunk%40src%40gui%40viewmanager.py/106/gtk_osxapplication/python

def Application():
	if sys.platform == "darwin":
		try:
			# This worked with the first runtime that we built.
			import gtk_osxapplication
			return gtk_osxapplication.OSXApplication()
		except ImportError:
			# This works with the second. We can find no explanation of the name change.
			import gtkosx_application
			return gtkosx_application.Application()
	else:
		return None

def adjust_menus(macapp, builder, on_exit):
	# Hide the main menu at the top of the window and ask the
	# MacOSX application menu to accept its items.
	main_menu = builder.get_object("MainMenu")
	main_menu.hide()
	macapp.set_menu_bar(main_menu)

	# Hide our File/Exit menu item (and the separator above it)
	# and connect to the MacOSX Quit item in the application menu. 
	builder.get_object("MenuFileExitSeparator").hide()
	builder.get_object("MenuFileExit").hide()
	macapp.connect("NSApplicationBlockTermination", on_exit)

	macapp.insert_app_menu_item(builder.get_object("MenuHelpAbout"), 0)


	
