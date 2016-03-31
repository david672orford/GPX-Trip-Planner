# gpx_satnavs.py
# Copyright 2013, 2014, Trinity College
# Interface to GPS navigators
# Last modified: 27 December 2014

import sys
import subprocess
import gobject
import gtk
import os
import glob
import re
from gpx_data_gpx import GpxWriter, GpxWaypoint, GpxRoute, GpxRoutePoint

# Use one of these to interact with the GPS receivers and navigators.
# It uses the classes defined below to implement communcation with
# various types of GPS devices.
class GpxSatnavs(object):
	def __init__(self, ui):
		self.ui = ui

		# This list store contains a list of the available GPSrs. The functions
		# which send or receive data from a GPSr require an index into this
		# array as a parameter to indicate which device the user selected.
		self.liststore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)

		# Static entries for these until we implement auto detection.
		self.liststore.append([ "Garmin Etrex", GpxGpsrGpsbabel("garmin", "usb:") ])
		self.liststore.append([ "Delorme PN", GpxGpsrGpsbabel("delbin", "usb:") ])
		self.liststore.append([ "Tomtom BT", GpxGpsrTomtomBT(("00:13:6C:1E:CE:AB", 2)) ])

		self.scan()

	# Search for GPS receivers and update the liststore.
	def scan(self):
		print "Scanning for satnavs:"
		path_list = []

		# Possible paths
		if sys.platform.startswith("linux"):
			mounts = open("/proc/mounts")
			for line in mounts:
				mountpoint, fstype = line.split(" ")[1:3]
				if fstype == "vfat":
					path_list.append(mountpoint)
			mounts.close()

		elif sys.platform == "win32":
			for drive in ("d","e","f","g","h","i","j","k"):
				path_list.append("%s:\\" % drive)

		elif sys.platform == "darwin":
			# FIXME: code missing
			pass

		# Try the possible paths
		for path in path_list:
			print "  %s" % path

			# Is it a Tomtom One?
			test_path = os.path.join(path, "ttgo.bif")
			if os.path.exists(test_path):
				f = open(test_path, "r")
				pattern = re.compile("DeviceName=([^\r\n]+)")
				for line in f:
					m = pattern.match(line)
					if m:
						self.liststore.append([ m.group(1), GpxGpsrTomtomMS(path) ])
						break
				f.close()
				continue

			# Is it a Garmin Nuvi?
			test_path = os.path.join(path, "Garmin", "GarminDevice.xml")
			if os.path.isfile(test_path):
				self.liststore.append([ "Garmin Nuvi", GpxGpsrGarminMS(path) ])
				continue

	# Download everything that is in the designated GPS receiver's memory.
	# Return True if at least one object was received.
	def load(self, gpsr_index, datastore):
		print "Loading from GPSr %d (%s)..." % (gpsr_index, self.liststore[gpsr_index][0])
		reader = self.liststore[gpsr_index][1]
		try:
			return reader.load(datastore, self.ui)
		except Exception as e:
			self.ui.error_dialog_exception(_("Reading from GPS receiver"), e)
			return False

	# Send everything that we can back to the designated GPS receiver.
	# Return True on success.
	#
	# NOTE: This is not used currently due to difficulty actually implementing
	# this functionality, particularly on Garmin GPSrs which have a morbid
	# fear of allowing the user to overwrite existing data and instead
	# permutate the names of the saved objects so as to leave their previous
	# versions undisturbed.
	#def save(self, gpsr_index, datastore):
	#	print "Saving to GPSr %d (%s)..." % (gpsr_index, self.liststore[gpsr_index][0])
	#	try:
	#		writer = self.liststore[gpsr_index][1]
	#		return writer.save(datastore, self.ui)
	#	except Exception as e:
	#		self.ui.error_dialog_exception(_("Writing to GPS receiver"), e)
	#		return False

	# Send a single object (such as a waypoint or a route) to the GPS receiver.
	# Return True on success.
	def send_obj(self, gpsr_index, obj):
		print "Sending object to GPSr %d (%s): %s" % (gpsr_index, self.liststore[gpsr_index][0], obj)
		try:
			writer = self.liststore[gpsr_index][1]
			return writer.send_obj(obj, self.ui)
		except Exception as e:
			self.ui.error_dialog_exception(_("Sending object to GPS receiver"), e)
			return False

#=============================================================================
# Anything supported by Gpsbabel
# This includes Garmin's protocol for communicating with hiking GPSrs.
#=============================================================================
class GpxGpsrGpsbabel(object):
	def __init__(self, data_format, data_file):
		self.data_format = data_format
		self.data_file = data_file
	def load(self, datastore, ui):
		command = ["gpsbabel",
			"-w", "-r", "-t",									# waypoints, route, tracks
			"-i", self.data_format, "-f", self.data_file,		# in Garmin format from USB connected GPSr
			"-o", "gpx", "-F", "-",								# in GPX format to stdout
			]
		print "Running:", command
		connexion = subprocess.Popen(command, stdout=subprocess.PIPE)
		datastore.load_gpx(connexion.stdout)	
		retcode = connexion.wait()
		if retcode != 0:
			ui.error("Gpsbabel could not read from GPSr")
			return False
		return True
	def send_obj(self, obj, ui):
		command = ["gpsbabel",
			"-w", "-r", "-t",								# waypoints, route, tracks
			"-i", "gpx", "-f", "-",							# in GPX format from stdin
			"-o", self.data_format, "-F", self.data_file,	# in Garmin format to USB connected GPSr
			]
		print "Running:", command
		connexion = subprocess.Popen(command, stdin=subprocess.PIPE)
		obj.write(GpxWriter(connexion.stdin))
		connexion.stdin.close()		# send EOF to Gpsbabel
		retcode = connexion.wait()
		if retcode == 0:
			return True
		else:
			print "Return code:", retcode
			ui.error("Gpsbabel could not write to GPSr")
			return False

#=============================================================================
# Garmin Nuvi in mass-storage mode
#=============================================================================
class GpxGpsrGarminMS(object):
	def __init__(self, path):
		self.gpx_path = os.path.join(path, "GPX")
		self.seq = 1
	def load(self, datastore, ui):
		datastore.load_gpx(open(os.path.join(self.gpx_path, "Current.gpx"), "r"))
		return True
	def send_obj(self, obj, ui):
		filename = None
		while filename is None or os.path.exists(filename):
			filename = os.path.join(self.gpx_path, "Trip Planner %03d.gpx" % self.seq)
			self.seq += 1
		writer = GpxWriter(open(filename, "w"))
		obj.write(writer)
		return True

#=============================================================================
# Tomtom Go, One, etc. in mass-storage mode
#=============================================================================
class GpxGpsrTomtomMS(object):
	def __init__(self, path):
		self.itn_path = "%s/itn" % path
	def load(self, datastore, ui):
		from pykarta.formats.tomtom_itn import ItnReader
		for filename in glob.glob("%s/*.itn" % self.itn_path):
			print "Reading", filename
			reader = ItnReader(open(filename, "r"))
			route = GpxRoute()
			route.name = os.path.splitext(os.path.basename(filename))[0]
			datastore.routes.append(route)
			for point in reader:
				route_point = GpxRoutePoint(point.lat, point.lon)
				route_point.desc = point.description
				if point.stopover:
					route_point.type = "stop"
				route.append(route_point)
		return True
	def send_obj(self, obj, ui):
		if type(obj) is GpxWaypoint or type(obj) is GpxRoutePoint:
			return self.write_itn([obj], obj.name) != None
		elif type(obj) is GpxRoute:
			return self.write_itn(obj, obj.name) != None
		else:
			ui.error("Only points and routes may be sent to Tomtom GPSrs.")
			return False
	def write_itn(self, obj, name):
		from pykarta.formats.tomtom_itn import ItnPoint, ItnWriter
		filename = os.path.join(self.itn_path, "%s.itn" % name)
		print "Creating:", filename
		writer = ItnWriter(open(filename, "w"))
		for point in obj:
			writer.add(ItnPoint(point.lat, point.lon, point.desc, point.type == 'stop'))
		writer.save()
		writer.write()
		return filename

#=============================================================================
# Tomtom with a Bluetooth listener installed
#=============================================================================
class GpxGpsrTomtomBT(object):
	def __init__(self, address):
		self.address = address
	def load(self, datastore, ui):
		return False
	def send_obj(self, obj, ui):
		if type(obj) is not GpxWaypoint and type(obj) is not GpxRoutePoint:
			ui.error("Only points may be sent to Tomtom GPSrs over Bluetooth.")
			return False
		from pykarta.gps.satnav import TomtomBT
		tomtom = TomtomBT(self.address)
		tomtom.NavigateToCoordinates(obj.lat, obj.lon, obj.name)

