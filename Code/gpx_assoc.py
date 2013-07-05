# gpx_assoc.py
# Copyright 2013, Trinity College
# Last modified: 14 January 2013

import sys
import os
import subprocess

def set_associations(ui):
	launcher = os.path.abspath(os.getenv("LAUNCHER"))
	print "Launcher:", launcher
	try:
		if sys.platform == 'win32':
			subprocess.check_call(['assoc', '.gpx=gpxfile'])
			subprocess.check_call(['assoc', '.loc=locfile'])
			subprocess.check_call(['ftype', 'gpxfile="%s" "%1"' % launcher])
			subprocess.check_call(['ftype', 'locfile="%s" --import "%1"' % launcher])
		elif os.getenv("XDG_DATA_DIRS", None) != None:
			xdg_installer = os.path.join(sys.path[0], "xdg")
			subprocess.check_call(["%s/install" % xdg_installer, xdg_installer, launcher])
		else:
			ui.error("Not yet implemented for %s" % sys.platform)
	except Exception as e:
		ui.exception(_("Setting file associations"), e)

