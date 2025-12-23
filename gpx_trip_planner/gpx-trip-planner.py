#! /usr/bin/python3
# Copyright 2013--2025, Trinity College

"""Launch the application"""

import sys
import os

# Determine path to file containing socket number.
# All of these directories are user-private.
if sys.platform == "darwin":
	server_file_dir = os.getenv("TMPDIR")
elif sys.platform == "win32":
	server_file_dir = os.getenv("TMP")
else:
	server_file_dir = os.path.join(os.environ["HOME"], ".cache")
server_file = os.path.join(server_file_dir, "gpx-trip-planner-socket")
print("server_file:", server_file)

# Parse command line
progname = sys.argv.pop(0)
profile_dir = "."
import_mode = False
while len(sys.argv) >= 1 and sys.argv[0].startswith("-"):
	opt = sys.argv.pop(0)
	if opt.startswith("--profile-dir="):
		profile_dir=opt.split("=",1)[1]
	elif opt == '--import':
		import_mode = True
	elif opt.startswith("-psn_"):	# MacOSX "process serial number"
		pass
	else:
		sys.stderr.write("Invalid option: %s\n" % opt)
		sys.exit(1)

# If we are to import files, try to pass them to an existing instance.
if import_mode:
	import urllib.request, urllib.error, urllib.parse
	try:
		fh = open(server_file, "r")
		port = int(fh.read())
		for filename in sys.argv:
			url = "http://127.0.0.1:%d/import?%s" % (port, os.path.abspath(filename))
			print(url)
			http = urllib.request.urlopen(url)
			print(http.read())
		sys.exit(0)
	except Exception as e:
		print("Failed to contact running instance:", str(e))

#=============================================================================
# Start a new instance of the GPX Trip Planner
#=============================================================================

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, GObject, Gtk
import pyapp.i18n
from gpx_gui import GpxGUI
from gpx_server import GpxServer

pyapp.i18n.initialize(domain="gpx-trip-planner")

# Application object
trip_planner = GpxGUI(profile_dir)

# Start embedded web server thread
server = GpxServer(trip_planner)
port = server.get_port()
print("Server is on port %d." % port)
open(server_file, "w").write("%d\n" % port)
trip_planner.set_server(server)

# Pass file names from command line
if import_mode:
	GLib.idle_add(trip_planner.import_files, sys.argv)
else:
	GLib.idle_add(trip_planner.open_files, sys.argv)

# Start Gtk event loop.
Gtk.main()

sys.exit(0)
