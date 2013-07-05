#! /usr/bin/python
# pykarta/gps/live.py
# GPS receiver support
# Copyright 2013, Trinity College Computing Center
# Last modified: 26 March 2013

import os
import sys
import re
import gobject

class BadConfig(Exception):
	pass

class BadConfigMissing(BadConfig):		# configuration missing entirely
	pass

class BadConfigInterface(BadConfig):	# invalid interface
	pass

class BadConfigParams(BadConfig):		# incorrect number of parameters
	pass

class BadConfigImport(BadConfig):		# missing python module
	pass

class BadConfigMissingProg(BadConfig):	# external program missing
	pass

class BadConfigOther(BadConfig):
	pass

# This is the object passed to the callback to represent the
# location of the GPS receiver.
class GPSFix(object):
	def __str__(self):
 		return "(%f, %f) %s %s" % (self.lat, self.lon, self.heading, self.speed)

def GPSlistener(**kwargs):
	if not "interface" in kwargs:
		raise BadConfigMissing
	interface_name = kwargs['interface'].split(',')[0]
	if interface_name == "gpsd":
		return GPSlistenerGpsd(**kwargs)
	if interface_name == "gpsbabel":
		return GPSlistenerGpsbabel(**kwargs)
	raise BadConfigInterface(interface_name)

class GPSlistenerBase(object):
	def __init__(self, interface=None, position_callback=None, debug_level=0):
		self.position_callback = position_callback
		self.debug_level = debug_level

	def debug(self, level, message):
		if self.debug_level >= level:
			print message

class GPSlistenerGpsd(GPSlistenerBase):
	def __init__(self, **kwargs):
		GPSlistenerBase.__init__(self, **kwargs)
		self.gpsd = None

		interface = kwargs['interface'].split(',')
		if len(interface) != 1 and len(self.interface) != 2:
			raise BadConfigParams

		self.watch_in = None

		try:
			import gps
		except ImportError:
			raise BadConfigImport

		params = {
			'mode': gps.WATCH_ENABLE|gps.WATCH_JSON|gps.WATCH_SCALED,
			'verbose': 0
			}
		if len(interface) == 2:
			params['host'], params['port'] = interface[1].split(':')
		print "  gps.gps(", params, ")"
		try:
			self.debug(1, "Connecting to GPSd...")
			self.gpsd = gps.gps(**params)
		except Exception as e:
			raise BadConfigOther("%s: %s" % (type(e).__name__, str(e)))

		self.watch_in = gobject.io_add_watch(self.gpsd.sock, gobject.IO_IN, self.packet)

	# Called whenever a packet is received from GPSd
	def packet(self, source, condition):
		import gps
		if self.gpsd.read() == -1:					# we used to call .poll(), but it is gone
			self.position_callback(None, "read() failed on GPSd socket")
			self.close()
			return False
		self.debug(2, "GPSd: %s" % str(self.gpsd))
		if self.gpsd.valid & gps.PACKET_SET:		# If there is a complete JSON message available,
			data = self.gpsd.data
			# If it is a position report,
			if data['class'] == 'TPV' and 'lat' in data and 'lon' in data:
				fix = GPSFix()
				fix.lat = data['lat']
				fix.lon = data['lon']
				fix.heading = data.get('track', None)
				fix.speed = data.get('speed', None)
				self.position_callback(fix, None)
		return True

	# Cleanly shut down the listener
	def close(self):
		if self.watch_in:
			gobject.source_remove(self.watch_in)
			self.watch_in = None

		if self.gpsd:
			self.debug(2, "  Closing connexion to GPSd...")
			self.gpsd.close()
			self.debug(1, "  Connexion to GPS receiver shut down.")
			self.gpsd = None

class GPSlistenerGpsbabel(GPSlistenerBase):
	def __init__(self, **kwargs):
		GPSlistenerBase.__init__(self, **kwargs)
		self.gpsbabel = None
		self.terminating = False

		import subprocess
		import thread

		interface = kwargs['interface'].split(',')
		if len(interface) != 3:
			raise BadConfigParams

		stylefile = os.path.join(os.path.dirname(__file__), "gpsbabel_stream.style")
		command = ["gpsbabel", "-T",
			"-i", interface[2],
			"-f", interface[1],
			"-o", "xcsv,style={stylefile}".format(stylefile=stylefile),
			"-F", "-"]

		self.debug(1, "Launching Gpsbabel: %s" % command)
		self.gpsbabel = subprocess.Popen(command, stdout=subprocess.PIPE)

		thread.start_new_thread(self.read_thread, ())

	def read_thread(self):
		while True:
			data = self.gpsbabel.stdout.readline().strip()
			self.debug(3, "Data from GPSBabel: %s" % data)
			if data == "":
				break
			lat, lon, alt, speed, heading, time = data.split(',')
			fix = GPSFix()
			fix.lat = float(lat)
			fix.lon = float(lon)
			fix.heading = float(heading)
			fix.speed = float(speed)
			gobject.idle_add(lambda: self.position_callback(fix, None), priority=gobject.PRIORITY_HIGH)
		if self.terminating:
			error = None
		else:
			error = "Gpsbabel terminated unexpectedly"
		gobject.idle_add(lambda: self.position_callback(None, error), priority=gobject.PRIORITY_HIGH)

	# Cleanly shut down the listener
	def close(self):
		if self.gpsbabel:
			self.debug(2, "  Shutting down GPSbabel...")
			self.terminating = True
			self.gpsbabel.terminate()
			self.gpsbabel.wait()
			self.debug(1, "  Connexion to GPS receiver shut down.")
			self.gpsbabel = None

if __name__ == "__main__":
	def callback(fix, error_detail):
		if fix:
			print "Fix: %s" % str(fix)
		else:
			print "Connexion to GPS receiver lost: %s" % error_detail
	gobject.threads_init()
	gps_obj = GPSlistener(
		#interface="gpsd",
		interface="gpsbabel,usb:,garmin",
		position_callback=callback,
		debug_level=5
		)
	loop = gobject.MainLoop()
	loop.run()

