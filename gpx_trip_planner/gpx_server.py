#=============================================================================
# gpx_server.py
# Copyright 2013--2023, Trinity College
# Last modified: 26 March 2023
#=============================================================================

from gi.repository import GObject
import _thread
import http.server
import re
import pyapp.gtk_thread

class GpxRequestHandler(http.server.BaseHTTPRequestHandler):

	def do_GET(self):
		print("HTTP Server: GET %s" % self.path)
		server_obj = self.server.parent

		# Instruction to import a file as if thru File->Import
		m = re.match('^/import\?(.+)$', self.path)
		if m:
			GObject.idle_add(server_obj.trip_planner.import_files, [m.group(1)])
			self.send_response(200)
			self.send_header("Content-Type", "text/plain")
			self.send_header("Content-Length", "0")
			return

		# Request for data previosly passed to our add_temp() method?
		m = re.match('^/temp/(.+)$', self.path)
		if m:
			index = int(m.group(1))
			
			if index in server_obj.temp:			# if such a file exists,
				data = server_obj.temp[index]
				print(data)
				self.send_response(200)
				self.send_header("Content-Type", "application/xml")
				self.send_header("Content-Length", len(data))
				self.end_headers()
				self.wfile.write(data)
				del server_obj.temp[index]
				return

		# Test of function call into GUI
		m = re.match('^/test$', self.path)
		if m:
			bbox = server_obj.call_wrapper.call(lambda: server_obj.trip_planner.map.get_bbox())
			data = str(bbox) + "\n"
			self.send_response(200)
			self.send_header("Content-Type", "text/plain")
			self.send_header("Content-Length", len(data))
			self.end_headers()
			self.wfile.write(data)
			return

		self.send_response(404, "File not found")

class GpxServer(object):
	def __init__(self, trip_planner):
		print("Starting web server...")
		self.httpd = http.server.HTTPServer(("127.0.0.1", 0), GpxRequestHandler)
		self.httpd.parent = self	# cheating: we really should subclass

		self.trip_planner = trip_planner
		self.temp = {}
		self.temp_index = 0

		self.call_wrapper = pyapp.gtk_thread.GtkCallWrapper()

		_thread.start_new_thread(self.httpd.serve_forever, ())

	# Return the number of the port on which the server is listening.
	def get_port(self):
		ip, port = self.httpd.server_address
		return port

	# Store the data provided and return a URL from which it may later be
	# downloaded. It may be downloaded only once. This is used in cases
	# where we want to pass data to another program such as JOSM. The data
	# is first passed to this function, then the URL is sent to the program.
	def add_temp(self, data):
		self.temp_index += 1
		self.temp[self.temp_index] = data
		return "http://127.0.0.1:%d/temp/%d" % (self.get_port(), self.temp_index)

