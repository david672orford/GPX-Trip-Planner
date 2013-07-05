#! /usr/bin/python
# lib/webkit_robot.py
# Copyright 2013, Trinity College Computing Center
# Last modified: 17 January 2013

import gobject
import gtk
import webkit
import re
import urllib
import urlparse
import os
import tempfile

#
# This is a web browser widget based on Webkit. It has a simple macro 
# facility similar to Expect.
#
#
# References:
# * http://webkitgtk.org/reference/index.html
#
class WebkitRobot(gtk.VBox):
	def __init__(self, config=None, file_download_cb=None, data_download_cb=None, controls=True, button_stop=True, button_refresh=True):
		gtk.VBox.__init__(self)

		self.config = config
		self.file_download_cb = file_download_cb
		self.data_download_cb = data_download_cb

		# derived classes may override
		self.login_macro = []					# run before first macro set with macro() method
		self.triggerable_macros = []			# run when loaded URL matches regexp
		self.go_back_after_download = True		# useful when download link on leaf page
		self.user_script = None					# Greasymonkey-style user script
		self.allowed_domains = None

		# Status
		self.running_macro = []
		self.current_uri = None
		self.download_ext = None
		self.ajax_code_sent = False				# Ajax completion handler installed
		self.ajax_complete_regexp = None		# Regexp to compare to URI of completed Ajax request

		# Web browser widget (inside scroller)
		scroller = gtk.ScrolledWindow()
		self.webkit = webkit.WebView()
		self.webkit.connect('console-message', self.console_message_cb)
		self.webkit.connect('navigation-policy-decision-requested', self.navigation_policy_decision_requested_cb)
		self.webkit.connect('resource-request-starting', self.resource_request_starting_cb)
		self.webkit.connect('mime-type-policy-decision-requested', self.mime_type_policy_decision_requested_cb)
		self.webkit.connect('download-requested', self.download_requested_cb)
		self.webkit.connect('load-finished', self.finished_loading_cb)				# waits for images
		scroller.add(self.webkit)

		# Enable Webkit debugger
		settings = self.webkit.get_settings()
		settings.set_property("enable-developer-extras", True)
		settings.set_property("enable-plugins", False)
		self.inspector = self.webkit.get_web_inspector()
		self.inspector.connect("inspect-web-view", self.inspect_web_view_cb)
		self.webkit.connect("button-press-event", self.mouse_click_cb)

		# Panel with control buttons at top.
		if controls:
			self.panel = gtk.HBox()
			self.button_create(gtk.STOCK_GO_BACK, self.webkit.go_back)
			self.button_create(gtk.STOCK_GO_FORWARD, self.webkit.go_forward)
			if button_stop:
				self.button_create(gtk.STOCK_STOP, self.webkit.stop_loading)
			if button_refresh:
				self.button_create(gtk.STOCK_REFRESH, self.webkit.reload)
			self.pack_start(self.panel, False, False, 5)
			self.panel.show_all()

		# Browser content pane has rest of space.
		self.pack_start(scroller, True, True)
		scroller.show_all()

	def button_create(self, stock_icon, clicked_function):
		button = gtk.Button(stock=stock_icon)
		self.panel.pack_start(button, False, False, 5)
		button.connect("clicked", self.button_handler, clicked_function)
		
	def button_handler(self, widget, function):
		print "Button:", widget.get_label()
		function()

	# Some evil websites install an empty handler for the context menu. This
	# prevents us from opening the web inspector.
	def mouse_click_cb(self, widget, gdkevent):
		if gdkevent.button == 3:
			# This should be a general solution, but it does not work for ReferenceUSA.
			#self.webkit.execute_script("document.oncontextmenu=null")
			# This works for ReferenceUSA. We need a general solution.
			self.webkit.execute_script("enableScraping()")
		return False

	# Called if the user opens the web inspector.
	# We create a new webview for it.
	def inspect_web_view_cb(self, inspector, inspected_web_view):
		window = gtk.Window()
		window.set_default_size(800, 600)
		inspector_web_view = webkit.WebView()
		window.add(inspector_web_view)
		window.show_all()
		return inspector_web_view
	
	# We use a debug function so that it will be easy to disable debugging
	# messages when we don't need them.
	def debug(self, message):
		if True:
			print message

	# Receive a message sent to the Javascript console.
	def console_message_cb(self, view, message, line, source_id):
		match = re.match("^([^:]+):(.+)$", message)
		if match:
			name = match.group(1)
			value = match.group(2)
			if name == "AJAX_COMPLETE":
				if self.ajax_complete_regexp.search(value):
					self.ajax_complete_regexp = None
					self.macro_next()
			elif name == "EXTRACT":
				self.extracted_data_processor(value)
			else:
				self.debug("console: %s\n" % message.rstrip())
		return True

	# We could use this to prevent navigation to other sites (such as those
	# which are serving advertisements).
	def navigation_policy_decision_requested_cb(self, view, frame, req, action, pol_dec):
		url = req.get_uri()
		print "Navigating to:", url

		if not self.approved_url(url):
			print " rejected"
			pol_dec.ignore()
			return True

		return False

	def resource_request_starting_cb(self, view, frame, resource, request, response):
		url = request.get_uri()
		print "Resource request starting:", url
		if not self.approved_url(url):
			print " rejected"
			request.set_uri("about:blank")

	def approved_url(self, url):
		if self.allowed_domains is not None:
			url_hostname = urlparse.urlparse(url).netloc.split(':')[0]
			#print "url_hostname:", url_hostname
			for domain in self.allowed_domains:
				#print "domain:", domain
				if url_hostname == domain or url_hostname.endswith(".%s" % domain):
					return True
			return False
		return True

	# Override default handling for certain MIME types.
	def mime_type_policy_decision_requested_cb(self, view, frame, req, mime_type, pol_dec):
		url = req.get_uri()
		self.debug("MIME type of %s: %s" % (url, mime_type))

		# Arrange to download CSV files.
		if mime_type == 'text/csv' or mime_type == 'text/comma-separated-values':
			self.download_ext = "csv"
			pol_dec.download()
			return True

		# Arrange to download CSV files.
		if mime_type == 'application/octet-stream' and url.find("vcard"):
			self.download_ext = "vcf"
			pol_dec.download()
			return True

		# Otherwise, ask for default handling.
		return False

	# Supply the answers to questions about a download that it is about to start.
	def download_requested_cb(self, view, download):
		self.debug("============================================")
		self.debug("Download: %s" % download.get_uri())

		# Pick a file name for saving the downloaded data. This is a little
		# tricky because Webkit requires us to express the file name
		# as a file URI.
		fi, filename = tempfile.mkstemp(prefix="download-%s-" % self.__class__.__module__, suffix=".%s" % self.download_ext)
		os.close(fi)
		dest_uri = "file:///" + filename.replace('\\', '/')		# Win32 uses backslashes
		print "Save to: %s" % dest_uri
		download.set_destination_uri(dest_uri)

		# Tell Webkit that the download may go again.
		download.start()

		# Periodically call a function which will monitor the download. This
		# is necessary since Webkit does not have a progress signal.
		gobject.timeout_add_seconds(1, self.download_tick_cb, download)

		return True

	# This runs once a second until the download is complete.
	def download_tick_cb(self, download):
		progress = download.get_progress()
		self.debug("Download progress: %s" % progress)
		self.debug("Download status: %s" % str(download.get_status()))
		if progress == 1.0:
			self.debug("============================================")
			self.debug("Download finished: %s" % download.get_uri())
			filename = download.get_destination_uri()
			filename = filename[8:]		# remove "file:///"
			self.debug("Saved as: %s" % filename)
			if self.file_download_cb:
				self.file_download_cb(filename)
			if self.go_back_after_download:
				self.webkit.go_back()
			return False	# stop timer
		return True			# continue timer

	# This is called whenever a new page has been completely loaded.
	def finished_loading_cb(self, view, frame):
		uri = frame.get_uri()
		self.debug("Finished loading: %s" % uri)

		# For some reason, this callback can fire more than once.
		if uri == self.current_uri:
			self.debug("(Duplicate finished loading signal)")
			return
		self.current_uri = uri

		# The Jquery Ajax completion handler has not yet been installed.
		self.ajax_code_sent = False

		# There is a list of regular expressions which match web page URIs and
		# trigger the execution of macros when they do.
		for i in self.triggerable_macros:
			i_re, i_macro = i
			if i_re.search(uri):
				self.debug("Macro triggered")
				self.running_macro = i_macro[:]	# copy of macro
				break

		self.macro_next()

	# Take the next line in the macro and execute it.
	def macro_next(self):
		if len(self.login_macro):
			macro = self.login_macro
		else:
			macro = self.running_macro

		# If there are lines left in the macro,
		if len(macro):
			url = macro.pop(0)
			self.debug("Macro: %s" % url)

			# Execute Javascript and move on to the next instruction in the 
			# macro without waiting.
			match = re.match('^js_blind:(.+)$', url)
			if match:
				code = match.group(1)
				self.webkit.execute_script(code)
				self.macro_next()
				return

			# Execute Javascript that is expected to cause a new page to be
			# loaded. The next instruction in the macro will be triggered
			# when the new page finishes loading.
			match = re.match('^js_nav:(.+)$', url)
			if match:
				code = match.group(1)
				self.webkit.execute_script(code)
				return

			# Simply wait for the indicated number of milliseconds (?).
			match = re.match('^js_delay:(\d+):(.+)$', url)
			if match:
				self.webkit.execute_script(match.group(2))
				gobject.timeout_add(int(match.group(1)), self.wait_over_cb)
				return

			# Execute the code in the second parameter and wait for an Ajax request the 
			# URL of which matches the regexp in the first parameter to be completed.
			match = re.match('^js_ajax:([^:]+):(.+)$', url)
			if match:
				self.ajax_complete_regexp = re.compile(match.group(1))
				code = match.group(2)
				if not self.ajax_code_sent:		# If callback not yet attached,
					self.webkit.execute_script("$('#search').ajaxComplete(function(e, xhdr, settings){log('AJAX_COMPLETE:'+settings.url)});")
					self.ajax_code_sent = True
				self.webkit.execute_script(code)
				return

			# If we get this far, the macro instruction is probably
			# just the URL of the next page to load.
			self.webkit.open(url)
			return

		# If there is a Greasymonkey-style user script,
		elif self.user_script:
			self.webkit.execute_script(self.user_script)

	# Called when the delay specified by js_delay is over
	def wait_over_cb(self):
		self.macro_next()
		return False

	# Take a string, escape internal double quotes and enclose
	# the whole thing in double quotes.	
	def double_quote(self, string):
		string.replace('"', '\\"')
		return '"' + string + '"'

	#================================================
	# Methods for external use
	#================================================

	def set_html_content(self, text):
		self.webkit.load_string(text, "text/html", "utf-8", "")

	# Open a web page
	def open(self, url):
		self.macro([url])

	# Same as above but with automatic formatting of the query string
	def open_with_params(self, url, **args):
		list = []
		for key in args.keys():
			value = str(args[key])
			print " param:", key, value
			list.append("%s=%s" % (urllib.quote_plus(key), urllib.quote_plus(value)))
		list_str = "&".join(list)
		self.open("%s?%s" % (url, list_str))

	# Load a macro and set it running.
	def macro(self, macro):
		self.running_macro = macro
		self.macro_next()

	# Load Greasemonkey-like script
	def load_user_script(self, filename):
		self.user_script = open(filename, "r").read()

	# Override this if you want to processes log messages that begin with "EXTRACT:".
	# This is used as a way to extract data from the web page.
	def extracted_data_processor(self, data):
		pass

	# Print the web page.
	def do_print(self):
		self.webkit.get_main_frame().print_()

if __name__ == "__main__":
	import sys
	browser = WebkitRobot()
	browser.open(sys.argv[1])
	window = gtk.Window()
	window.set_default_size(1024, 600)
	window.connect('delete-event', lambda window, event: gtk.main_quit())
	window.add(browser)
	window.show_all()
	gtk.main()
	sys.exit(0)


