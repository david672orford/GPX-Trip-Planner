#! /usr/bin/python
# coding=utf-8
# i18n.py
# Last modified: 15 January 2013

import os
import sys
import __builtin__

# If _() has not yet been defined, define it as a noop. It will
# remain a noop until initialize() is called.
if not __builtin__.__dict__.has_key('_'):
	__builtin__.__dict__['_'] = lambda text: text
	__builtin__.__dict__['ngettext'] = lambda singular, plural, n: (singular if n == 1 else plural)

# Turn on the message string translator and set locale.
# References:
#  * http://docs.python.org/library/locale.html#access-to-message-catalogs
#  * http://www.pixelbeat.org/programming/i18n.html
# Argument domain is the "translation domain". A translation domain is a set of
# translations which apply to a program or set of programs.
def initialize(domain="territory-editor"):
	try:
		import gettext, locale

		# We keep our translation files in a private directory. Find it.
		localedir = os.path.join(sys.path[0], 'locale')

		# Since Gtk is linked against GNU Gettext (rather than Python's Gettext),
		# we must initialize GNU Gettext.
		locale.setlocale(locale.LC_ALL, "")

		# Since locale.bindtextdomain() is missing from the Win32 port
		# of Python, we must use ctypes to call it directly from the DLL.
		# See: http://gramps.1791082.n4.nabble.com/gtk-builder-issues-fixed-td1802872.html
		if os.name == 'nt':
			import ctypes
			libintl_dll = path_search('libintl-8.dll')
			#print "Loading %s..." % libintl_dll
			libintl = ctypes.cdll.LoadLibrary(libintl_dll)

			libintl.bindtextdomain(domain, localedir.encode(sys.getfilesystemencoding()))
			libintl.textdomain(domain)
			libintl.bind_textdomain_codeset(domain, "UTF-8")
			libintl.gettext.restype = ctypes.c_char_p

			#print libintl.gettext("Export", domain)
		else:
			locale.bindtextdomain(domain, localedir)

		# We must also tell Python's implemention of the GNU Gettext API 
		# where to find our translation files.
		gettext.bindtextdomain(domain, localedir)
		gettext.textdomain(domain)
		__builtin__.__dict__['_'] = gettext.gettext
		__builtin__.__dict__['ngettext'] = gettext.ngettext

	except Exception as e:
		print "Failed to set language:", e

def path_search(filename):
	for i in sys.path:
		pathname = os.path.join(i, filename)
		if os.path.exists(pathname):
			return pathname
	return None

if __name__ == "__main__":
	import gtk

	initialize()

	print _("Export")
	#print "Привет!"

	#print ngettext("man", "men", 1)
	#print ngettext("man", "men", 2)

	w = gtk.Window()
	b = gtk.Label(_("Export"))
	w.add(b)
	w.show_all()
	gtk.main()

