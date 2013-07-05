# pykarta/misc/__init__.py
# Copyright 2013, Trinity College
# Last modified: 22 February 2013

import os
import time
import weakref
import new
import sys

# Exception raised when it seems the Internet connexion is down.
class NoInet(Exception):
	pass

# Return the name of a directory where PyKarta may store cache files.
def get_cachedir():
	app_name = "PyKarta"

	# If there is a directory called "Cache" at the same level as the
	# "Code" directory, use that. This is for when we install on a thumdrive.
	if os.path.exists(os.path.join(sys.path[0], "..", "Cache")):
		cachedir = os.path.join(sys.path[0], "..", "Cache")

	# MacOSX
	elif sys.platform == "darwin":
		cachedir = os.path.join(os.getenv("HOME"), "Library", "Caches", app_name)

	# MS-Windows
	elif sys.platform == "win32":											# MS-Windows
		appdata = os.getenv("APPDATA")
		if appdata is None:
			raise AssertionError("APPDATA not defined!")
		cachedir = os.path.join(appdata, app_name)

	# Unix
	elif os.path.exists(os.path.join(os.getenv("HOME"), ".cache")):
		cachedir = os.path.join(os.getenv("HOME"), ".cache", app_name)

	# Fallback
	else:
		cachedir = os.path.join(app_dir, "..", "Cache")

	print "Cache directory:", cachedir
	return cachedir

# How many days ago was this file modified?
def file_age_in_days(filename):
	try:
		stat_result = os.stat(filename)
	except OSError:
		return None
	return (float(time.time() - stat_result.st_mtime) / 86400.0)

# The weakref module is unable to create a reference to a bound method. This can.
class BoundMethodProxy(object):
	def __init__(self, bound_method):
		self.im_self_ref = weakref.ref(bound_method.im_self)
		self.im_func = bound_method.im_func
		self.im_class = bound_method.im_class
	def __call__(self, *args, **kwargs):
		obj = self.im_self_ref()
		if obj is None:
			raise ReferenceError
		new.instancemethod(self.im_func, obj, self.im_class)(*args, **kwargs)

# How many tiles are covered by a rectangle of the indicated size (in tiles)
# toaken to the indicated number of zoom levels?
def tile_count(width, height, zoom_levels):
	total = 0
	for z in range(zoom_levels):
		total += (width * height)
		width *= 2
		height *= 2
	return total

# Take the data from the handle and write it to the indicated file.
# The file does not receive the indicted name until it is complete.
class SaveAtomically(object):
	def __init__(self, filename, backup=False):
		(base, ext) = os.path.splitext(filename)
		self.filename = filename
		self.tmp = "%s.tmp" % base
		self.bak = "%s.bak" % base
		self.fh = open(self.tmp, 'wb')
		self.backup = backup
	def write(self, data):
		self.fh.write(data)
	def close(self):
		self.fh.close()
		if os.path.exists(self.filename):
			if self.backup:
				if os.path.exists(self.bak):
					os.remove(self.bak)
				os.rename(self.filename, self.bak)
			else:
				os.unlink(self.filename)
		os.rename(self.tmp, self.filename)

