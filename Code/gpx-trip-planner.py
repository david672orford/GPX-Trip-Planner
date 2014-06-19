#! /usr/bin/python
#=============================================================================
# gpx-trip-planner.py
# Copyright 2013, Trinity College
# Last modified: 8 August 2013
#=============================================================================

import sys
import os

# Determine path to file containing socket number.
# All of these directories are user-private.
if sys.platform == "darwin":
	server_file_dir = os.getenv("TMPDIR")
elif sys.platform == "win32":
	server_file_dir = os.getenv("TMP")
else:
	server_file_dir = os.path.join(os.getenv("HOME"), ".cache")
server_file = os.path.join(server_file_dir, "gpx-trip-planner-socket")
print "server_file:", server_file

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
		sys.stderr.write("Invalid option: %s" % opt)
		sys.exit(1)

# If we are to import files, try to pass them to an existing instance.
if import_mode:
	import urllib2
	try:
		fh = open(server_file, "r")
		port = int(fh.read())
		for filename in sys.argv:
			url = "http://127.0.0.1:%d/import?%s" % (port, os.path.abspath(filename))
			print url
			http = urllib2.urlopen(url)
			print http.read()
		sys.exit(0)
	except Exception as e:
		print "Failed to contact running instance:", str(e)

#=============================================================================
# Start a new instance of the GPX Trip Planner
#=============================================================================

import gobject
import gtk
import pyapp.i18n
import pyapp.updater
from gpx_gui import GpxGUI
from gpx_server import GpxServer

pyapp.i18n.initialize(domain="gpx-trip-planner")

# Needed for Osm-GPS-Map on Win32
gobject.threads_init()

# Application object
trip_planner = GpxGUI(profile_dir)

# Start embedded web server thread
server = GpxServer(trip_planner)
port = server.get_port()
print "Server is on port %d." % port
open(server_file, "w").write("%d\n" % port)
trip_planner.set_server(server)

# Pass file names from command line
if import_mode:
	gobject.idle_add(trip_planner.import_files, sys.argv)
else:
	gobject.idle_add(trip_planner.open_files, sys.argv)

# Start Gtk event loop.
gtk.main()

print "Updates:", trip_planner.package_updates
pyapp.updater.install_updates(trip_planner.package_updates)

sys.exit(0)

