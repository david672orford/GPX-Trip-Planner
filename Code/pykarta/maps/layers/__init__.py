# encoding=utf-8
# pykarta/maps/layers/__init__.py
# Copyright 2013, Trinity College
# Last modified: 12 April 2013

import os
import errno
import threading
import httplib
import time
import socket
import gobject
import math
import cairo

try:
	from collections import OrderedDict
except ImportError:
	from pykarta.fallback.ordereddict import OrderedDict

try:
	import rsvg
except:
    import pykarta.fallback.rsvg as rsvg

from pykarta.misc import file_age_in_days, BoundMethodProxy, NoInet, tile_count, SaveAtomically
from pykarta.misc.http import simple_url_split, simple_urlopen, http_date
from pykarta.geometry import Point, radius_of_earth
from pykarta.maps.image_loaders import surface_from_file, surface_from_file_data
from pykarta.maps.projection import *

#=============================================================================
# Base of all map layers
#=============================================================================
class MapLayer(object):
	def __init__(self):
		self.name = None
		self.containing_map = None
		self.stale = False
		self.attribution = None

	# Called automatically when the layer is added to the container.
	# It is called again if offline mode is entered or left so that the layer
	# can make any necessary adjustments.
	def set_map(self, containing_map):
		self.containing_map = containing_map

	# Mark layer so that at next redraw its do_viewport() will be
	# called and ask the widget to redraw.
	def set_stale(self):
		if not self.stale:
			self.stale = True
			if self.containing_map is not None:
				self.containing_map.queue_draw()

	# Overridden in editable vector layers
	def set_tool(self, tool):
		pass

	# The viewport has changed. Select objects or tiles and
	# determine their positions.
	def do_viewport(self):
		pass

	# Draw the objects selected and positioned by do_viewport()
	def do_draw(self, ctx):
		pass

	# Mouse button pressed down while pointer is over map
	def on_button_press(self, gdkevent):
		return False

	# Mouse button released while pointer is over map
	def on_button_release(self, gdkevent):
		return False

	# Mouse pointer moving over map
	def on_motion(self, gdkevent):
		return False

#=============================================================================
# Base of all tile layers
#=============================================================================
class MapTileLayer(MapLayer):
	def __init__(self):
		MapLayer.__init__(self)
		self.ram_cache = OrderedDict()
		self.ram_cache_max = 1000
		self.zoom_min = 0
		self.zoom_max = 99
		self.tiles = []
		self.tile_scale_factor = None
		self.int_zoom = None
		self.tile_ranges = None

	def __del__(self):
		print "Map: tile layer %s destroyed" % self.name

	# Called whenever viewport changes
	def do_viewport(self):
		#print "New tiles viewport..."
		lat, lon, zoom = self.containing_map.get_center_and_zoom()
		tile_size = 256
		half_width_in_pixels = self.containing_map.width / 2.0
		half_height_in_pixels = self.containing_map.height / 2.0

		if type(zoom) == int:
			self.int_zoom = zoom
			self.tile_scale_factor = 1.0
		else:
			self.int_zoom = int(zoom + 0.5)
			self.tile_scale_factor = math.pow(2, zoom) / (1 << self.int_zoom)
		#print "zoom:", zoom
		#print "int_zoom:", self.int_zoom
		#print "tile_scale_factor:", self.tile_scale_factor

		# In print mode, try to double the resolution by using tiles
		# for one zoom level higher and scaling them down.
		if self.containing_map.print_mode and self.int_zoom < self.zoom_max:
			if self.tile_scale_factor is None:
				self.tile_scale_factor = 1.0
			self.int_zoom += 1
			self.tile_scale_factor /= 2.0

		# Make a list of the tiles to use used and their positions on the screen.
		self.tiles = []
		self.tile_ranges = None
		if self.int_zoom >= self.zoom_min and self.int_zoom <= self.zoom_max:
			center_tile_x, center_tile_y = project_to_tilespace(lat, lon, self.int_zoom)

			# Find out how many tiles (and factions thereof) are required to reach the edges.
			half_width_in_tiles = half_width_in_pixels / (float(tile_size) * self.tile_scale_factor)
			half_height_in_tiles = half_height_in_pixels / (float(tile_size) * self.tile_scale_factor)

			# Find the first and last tile row and column which will be at least
			# partially visible inside the viewport.
			x_range_start = int(center_tile_x - half_width_in_tiles)
			x_range_end = int(center_tile_x + half_width_in_tiles + 1)
			y_range_start = int(center_tile_y - half_height_in_tiles)
			y_range_end = int(center_tile_y + half_height_in_tiles + 1)

			# Eliminate tiles that are off the 'edge of the world' at the top
			# or the bottom. (Those that hang off at the left and right will
			# be wrapped around.)
			max_tile_coord = (1 << self.int_zoom) - 1
			y_range_start = max(0, min(max_tile_coord, y_range_start))
			y_range_end = max(0, min(max_tile_coord, y_range_end))

			# Step through the tiles in the grid appending them to a list of
			# those which do_draw() will render.
			xpixoff = (half_width_in_pixels - (center_tile_x - x_range_start) * tile_size * self.tile_scale_factor) / self.tile_scale_factor
			starting_ypixoff = (half_height_in_pixels - (center_tile_y - y_range_start) * tile_size * self.tile_scale_factor) / self.tile_scale_factor
			tile_size *= 0.998		# shave slightly less than 1/2 pixel in order to prevent rounding gaps between tiles
			for x in range(x_range_start, x_range_end + 1):
				ypixoff = starting_ypixoff
				for y in range(y_range_start, y_range_end + 1):
					#print " Tile:", x, y, xpixoff, ypixoff
					self.tiles.append((self.int_zoom, x % (1 << self.int_zoom), y, xpixoff, ypixoff))
					ypixoff += tile_size
				xpixoff += tile_size

			self.tile_ranges = (x_range_start, x_range_end, y_range_start, y_range_end)

	# Called whenever redrawing required
	def do_draw(self, ctx):
		#print "Draw tiles..."
		ctx.scale(self.tile_scale_factor, self.tile_scale_factor)

		progress = 1
		for tile in self.tiles:
			if not self.containing_map.lazy_tiles:
				numtiles = len(self.tiles)
				self.containing_map.feedback.progress(progress, numtiles, _("Downloading {layername} tile {progress} of {numtiles}").format(layername=self.name, progress=progress, numtiles=numtiles))
			zoom, x, y, xpixoff, ypixoff = tile

			tile_surface = self.load_tile_cached(zoom, x, y, True)
			if tile_surface is not None:
				ctx.set_source_surface(tile_surface, xpixoff, ypixoff)
				ctx.paint_with_alpha(self.opacity)

			else:
				for lower_zoom in range(zoom-1, self.zoom_min-1, -1):
					zoom_diff = zoom - lower_zoom
					bigger_tile = self.load_tile_cached(lower_zoom, x >> zoom_diff, y >> zoom_diff, False)
					if bigger_tile != None:
						ctx.save()
						ctx.translate(xpixoff, ypixoff)
						ctx.rectangle(0, 0, 256, 256)
						ctx.clip()
						scale = 1 << zoom_diff
						pixels = 256 >> zoom_diff
						mask = scale - 1
						ctx.scale(scale, scale)
						ctx.set_source_surface(bigger_tile, -(pixels * (x & mask)), -(pixels * (y & mask)))
						ctx.paint_with_alpha(self.opacity)
						ctx.restore()
						break

			progress += 1

	# This wraps load_tile() and caches the most recently used tiles in RAM.
	def load_tile_cached(self, zoom, x, y, may_download):
		#print "Tile:", zoom, x, y, may_download
		key = (zoom, x, y)
		try:
			result = self.ram_cache.pop(key)	# will reinsert below
			#print " cache hit"
		except KeyError:
			#print " cache miss"
			result = self.load_tile(zoom, x, y, may_download)
			if result == None and not may_download:
				return None
			if len(self.ram_cache) > self.ram_cache_max:		# trim cache?
				self.ram_cache.popitem(last=False)
		self.ram_cache[key] = result
		return result

	def ram_cache_invalidate(self, zoom, x, y):
		try:
			self.ram_cache.pop((zoom, x, y))
		except KeyError:
			print "cache_invalidate(): not in cache", zoom, x, y

	# Return the indicated tile as a Cairo surface. If it is not yet
	# available, return None.
	def load_tile(self, zoom, x, y, may_download):
		return None

# This layer draws tile outlines and puts z/x/y in the top left hand corner.
class MapTileLayerDebug(MapTileLayer):
	def do_draw(self, ctx):
		ctx.scale(self.tile_scale_factor, self.tile_scale_factor)
		ctx.set_line_width(1)
		ctx.set_source_rgb(1.0, 0.0, 0.0)
		ctx.select_font_face("sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
		ctx.set_font_size(12)
		for tile in self.tiles:
			zoom, x, y, xpixoff, ypixoff = tile
			ctx.save()
			ctx.translate(xpixoff, ypixoff)
			ctx.rectangle(0, 0, 256, 256)
			ctx.stroke()
			ctx.move_to(10, 22)
			ctx.show_text("%d/%d/%d" % (zoom, x, y))
			ctx.restore()

#=============================================================================
# TMS tile layer loaded over HTTP
#=============================================================================
class MapTileLayerHTTP(MapTileLayer):
	def __init__(self, tileset):
		MapTileLayer.__init__(self)
		self.tileset = tileset
		self.tileset_online_init_called = False

		# How long (in milliseconds) to wait after receiving a tile
		# for the next one to arrive before redrawing
		self.tile_wait = 200

		self.downloader = None
		self.timer = None
		self.missing_tiles = {}
		self.redraw_needed = False
		self.tile_ranges = None

	# Hook set_map() so that when this layer is added to the map it
	# can create a tile downloader and set it to either syncronous mode or 
	# asyncronous mode depending on whether we are doing this for print
	# or for the screen (where lazy tile loading is disirable).
	def set_map(self, containing_map):
		MapTileLayer.set_map(self, containing_map)
		# If this tileset has not yet had a chance to download metadata and
		# we are currently online, give it that chance now.
		if not self.containing_map.offline and not self.tileset_online_init_called:
			self.tileset.online_init()
			self.tileset_online_init_called = True
		# Copy metadata from the tileset to the layer.
		self.zoom_min = self.tileset.zoom_min
		self.zoom_max = self.tileset.zoom_max
		self.opacity = self.tileset.opacity
		self.attribution = self.tileset.attribution

		# If we are offline, create an object which can only find tiles in the cache.
		# If we are online, create an object which can also download tiles.
		if self.containing_map.offline:
			self.downloader = MapTileCacheLoader(
				self.tileset,
				self.containing_map.tile_cache_basedir,
				feedback=self.containing_map.feedback,
				)
		else:
			self.downloader = MapTileDownloader(
				self.tileset,
				self.containing_map.tile_cache_basedir,
				feedback=self.containing_map.feedback,
				done_callback=BoundMethodProxy(self.tile_loaded_cb) if self.containing_map.lazy_tiles else None,
				)

		# The RAM cache may reflect absence of tiles. Dump it.
		self.ram_cache = OrderedDict()

	# Return the indicated tile as a Cairo surface or None if it is
	# not (yet) available.
	def load_tile(self, zoom, x, y, may_download):
		filename, pending = self.downloader.load_tile(zoom, x, y, may_download)
		if pending:
			#print " lazy load"
			self.missing_tiles[zoom] = self.missing_tiles.get(zoom, 0) + 1
		if filename is not None:
			#print " %s" % result
			try:
				return surface_from_file(filename)
			except:
				self.containing_map.feedback.debug(1, " defective tile file: %s" % filename)
		return None

	# The tile downloader calls this when the tile has been received
	# and is waiting in the disk cache. Note that it is called from
	# the downloader thread, so we have to wrap schedual the work
	# in the gobject event loop. We set the priority high so that
	# these messages will be delivered before redraw requests.
	def tile_loaded_cb(self, *args):
		gobject.idle_add(lambda: self.tile_loaded_cb_idle(*args), priority=gobject.PRIORITY_HIGH)
	def tile_loaded_cb_idle(self, zoom, x, y, modified):
		self.containing_map.feedback.debug(2, "Tile received: %d %d,%d %s" % (zoom, x, y, str(modified)))

		# If the tile was modified, dump it from the RAM cache whether
		# it is still needed or not.
		if modified:
			self.ram_cache_invalidate(zoom, x, y)

		# If this tile is still needed.
		if self.tile_in_view(zoom, x, y):
			self.containing_map.feedback.debug(5, " Still needed")

			if modified:
				self.redraw_needed = True

			# If this is the last tile we were waiting for,
			self.missing_tiles[zoom] -= 1
			if self.missing_tiles[zoom] == 0:
				self.containing_map.feedback.debug(5, " All tiles in, immediate redraw")

				# If last tile arrived before timer expired,
				if self.timer is not None:
					self.containing_map.feedback.debug(5, " Canceling timer")
					gobject.source_remove(self.timer)
					self.timer = None

				# If at least one tile is new or modified,
				if self.redraw_needed:
					self.containing_map.queue_draw()
					self.redraw_needed = False

			# If some tiles still out, set a timer at the limit of or patience.
			else:
				self.containing_map.feedback.debug(5, " %d tiles to go" % self.missing_tiles[zoom])
				if self.timer == None:
					self.timer = gobject.timeout_add(self.tile_wait, self.timer_expired)

	def tile_in_view(self, zoom, x, y):
		if zoom != self.int_zoom:
			return False
		if self.tile_ranges is None:
			return False
		x_range_start, x_range_end, y_range_start, y_range_end = self.tile_ranges
		return (x >= x_range_start and x <= x_range_end and y >= y_range_start and y <= y_range_end)

	# In order to avoid a redraw storm as the tiles come in we hold
	# of until either they have all arrived or a timer expires. This
	# is called when it expires.
	def timer_expired(self):
		self.containing_map.feedback.debug(5, " Redraw timer expired.")
		self.containing_map.queue_draw()
		self.timer = None
		return False

	# Load tiles into the cache in anticipation of offline use.
	def precache_tiles(self, progress, max_zoom):
		if self.tile_ranges is not None:
			downloader = MapTileDownloader(
				self.tileset,
				self.containing_map.tile_cache_basedir,
				feedback=progress,
				delay=0.1
				)
	
			# Start downloading
			x_start, x_end, y_start, y_end = self.tile_ranges
			total = tile_count(x_end-x_start+1, y_end-y_start+1, max_zoom-self.int_zoom+1)
			print "Will download %d tiles" % total
			if total > 0:
				count = 0
				for z in range(self.int_zoom, max_zoom+1):
					for x in range(x_start, x_end+1):
						for y in range(y_start, y_end+1):
							count += 1
							progress.progress(count, total, _("Downloading %s tile %d of %d, zoom level is %d") % (self.name, count, total, z))
							if downloader.load_tile(z, x, y, True) is None:		# failed
								for seconds in range(10, 0, -1):
									progress.countdown(_("Retry in %d seconds...") % seconds)
									time.sleep(1.0)
					x_start *= 2
					x_end = x_end * 2 + 1
					y_start *= 2
					y_end = y_end * 2 + 1

	def reload_tiles(self):
		if self.tile_ranges is not None:
			x_range_start, x_range_end, y_range_start, y_range_end = self.tile_ranges
			zoom = self.int_zoom
			for x in range(x_range_start, x_range_end+1):
				for y in range(y_range_start, y_range_end+1):
					self.ram_cache_invalidate(zoom, x, y)
					local_filename = "%s/%s/%d/%d/%d" % (self.containing_map.tile_cache_basedir, self.tileset.key, zoom, x, y)
					try:
						os.unlink(local_filename)
					except OSError:
						pass	

#=============================================================================
# Download tiles using HTTP
# This uses httplib rather than urllib2 because the latter does not support
# persistent connexions.
#=============================================================================

class MapTileDownloader(object):
	def __init__(self, tileset, tile_cache_basedir, done_callback=None, feedback=None, delay=None):
		self.tileset = tileset
		self.tile_cache_basedir = tile_cache_basedir
		self.feedback = feedback
		self.done_callback = done_callback
		self.delay = delay

		if feedback is None:
			raise AssertionError

		# Should we start threads?
		self.threads = []
		if self.done_callback:		# multi-threaded mode
			self.syncer = threading.Condition()
			self.queue = []
			for i in range(3):		# number of threads
				thread = MapTileDownloaderThread(self, name="%s-%d" % (self.tileset.key, i))
				self.threads.append(thread)
				thread.start()
		else:						# syncronous mode
			self.syncer = None
			self.queue = None
			self.threads.append(MapTileDownloaderThread(self, name="%s-dummy" % self.tileset.key))

	# If the indicated tile is in the cache and is not too old, return its path
	# so that the caller can download it. If it is not, and there is no callback
	# function, download it immediately. If there is a callback function, put
	# it in the queue for a background thread the download.
	#
	# Returns:
	#  filename--None if not (yet) available
	#  pending--True if a callback is to be expected	
	def load_tile(self, zoom, x, y, may_download):
		debug_args = (self.tileset.key, zoom, x, y)
		self.feedback.debug(2, "Load tile %s %d/%d/%d" % debug_args)
		local_filename = "%s/%s/%d/%d/%d" % (self.tile_cache_basedir, self.tileset.key, zoom, x, y)
		result = None

		try:
			statbuf = os.stat(local_filename)
		except OSError:
			statbuf = None

		if statbuf is None:
			self.feedback.debug(3, " Not in cache")
		else:
			cachefile_age = (float(time.time() - statbuf.st_mtime) / 86400.0)
			self.feedback.debug(4, " Cache file age: %s" % cachefile_age)
			if cachefile_age > self.tileset.max_age_in_days:
				self.feedback.debug(3, " Old in cache")
				result = local_filename
			else:
				self.feedback.debug(3, " Fresh in cache")
				return (local_filename, False)

		# The caller may want the tile only if it is available instantly.
		# This is used when using scaled up tiles from a lower zoom level
		# to temporarily replace missing tiles.
		if not may_download:
			self.feedback.debug(2, " Caller does not want to download")
			return (result, False)

		remote_filename = self.tileset.get_path(zoom, x, y)
		if self.done_callback:
			self.feedback.debug(2, " Added to queue")
			self.enqueue((zoom, x, y, local_filename, remote_filename, statbuf))
			return (result, True)
		else:
			self.feedback.debug(2, " Downloading syncronously...")
			if self.threads[0].download_tile_worker(zoom, x, y, local_filename, remote_filename, statbuf):
				if self.delay:
					time.sleep(self.delay)
				return (local_filename, False)
			else:
				return (None, False)

	# Add an item to the word queue for the background threads
	def enqueue(self, item, clear=False):
		self.syncer.acquire()
		if clear:
			while len(self.queue):
				self.queue.pop(0)
		self.queue.insert(0, item)
		if item is None:
			self.syncer.notifyAll()
		else:
			self.syncer.notify()
		self.syncer.release()

	# This tile downloader is no longer needed. Shut down the background threads.
	def __del__(self):
		print "Destroying tile downloader..."
		if self.queue is not None:
			# Tell the threads to stop
			self.enqueue(None, clear=True)

			# Wait for them to stop
			#for thread in self.threads:
			#	self.feedback.debug(1, " Waiting for thread %s to stop..." % thread.name)
			#	thread.join()
			#self.feedback.debug(1, "All downloader threads have stopped.")
		else:
			if self.threads[0].conn is not None:
				self.threads[0].conn.close()

class MapTileDownloaderThread(threading.Thread):
	def __init__(self, parent, **kwargs):
		threading.Thread.__init__(self, **kwargs)
		self.daemon = True
		self.feedback = parent.feedback
		self.conn = None
		self.syncer = parent.syncer
		self.queue = parent.queue
		self.tileset = parent.tileset
		self.done_callback = parent.done_callback

	def run(self):
		while True:
			self.syncer.acquire()
			self.feedback.debug(3, "Thread %s is waiting..." % self.name)
			while len(self.queue) < 1:
				self.syncer.wait()
			item = self.queue[0]
			if item is not None:
				self.queue.pop(0)
			self.feedback.debug(3, "Thread %s received item: %s" % (self.name, str(item)))
			self.syncer.release()
			if item is None:				# signal to stop
				break
			while True:
				if self.download_tile_worker(*item):
					break
				self.feedback.debug(3, "Thread %s sleeping..." % self.name)
				time.sleep(10)
		if self.conn is not None:
			self.conn.close()
		self.feedback.debug(1, " Thread %s exiting..." % self.name)

	def download_tile_worker(self, zoom, x, y, local_filename, remote_filename, statbuf):
		debug_args = (self.tileset.key, zoom, x, y)
		self.feedback.debug(2, "Thread %s downloading tile %s %d/%d/%d" % ((self.name,) + debug_args))

		# Download the tile. This uses a persistent connection.
		try:
			# Send GET request
			if self.conn is None:
				hostname = self.tileset.get_hostname()
				self.feedback.debug(3, " Thread %s opening HTTP connexion to %s..." % (self.name, hostname))
				self.conn = httplib.HTTPConnection(hostname, timeout=30)
			self.feedback.debug(3, " GET %s" % remote_filename)
			hdrs = {}
			hdrs.update(self.tileset.extra_headers)
			if statbuf is not None:
				hdrs['If-Modified-Since'] = http_date(statbuf.st_mtime)
			self.conn.request("GET", remote_filename, None, hdrs)

			# Read response
			response = self.conn.getresponse()

		except socket.gaierror:
			raise NoInet
		except socket.error, msg:
			self.feedback.debug(1, "  %s/%d/%d/%d: Socket error: %s" % (debug_args + (msg,)))
			self.feedback.error(_("Socket error: %s") % msg)
			self.conn = None		# close
			return False
		except httplib.BadStatusLine:
			self.feedback.debug(1, "  %s/%d/%d/%d: httplib.BadStatusLine" % debug_args)
			self.feedback.error(_("Invalid HTTP status line received from server"))
			self.conn = None		# close
			return False
		except httplib.ResponseNotReady:
			self.feedback.error(_("No response received from server"))
			self.conn = None		# close
			return False

		content_length = response.getheader("content-length")
		content_type = response.getheader("content-type")
		self.feedback.debug(5, "  %s/%d/%d/%d: %d %s %s %s bytes" % (debug_args + (response.status, response.reason, content_type, str(content_length))))

		if response.status == 304:
			self.feedback.debug(1, "  %s/%d/%d/%d: not modified" % debug_args)
			response.read()					# discard
			fh = open(local_filename, "a")	# touch
			fh.close()
			modified = False

		else:
			if response.status != 200:
				self.feedback.debug(1, "  %s/%d/%d/%d: unacceptable response status: %d %s" % (debug_args + (response.status, response.reason)))
				response_body = response.read()
				if response_body != "" and content_type.startswith("text/"):
					self.feedback.debug(1, "%s" % response_body.strip())
				return True	 				# give up on tile

			if not content_type.startswith("image/"):
				self.feedback.debug(1, "  %s/%d/%d/%d: non-image MIME type: %s" % (debug_args + (content_type,)))
				response_body = response.read()
				if content_type.startswith("text/"):
					self.feedback.debug(1, "%s" % response_body.strip())
				return True	 				# give up on tile
	
			if content_length is not None and int(content_length) == 0:
				self.feedback.debug(1, "  %s/%d/%d/%d: empty response" % debug_args)
				response.read()
				return True					# give up on tile
	
			# Make the cache directory which holds this tile, if it does not exist already.
			local_dirname = os.path.dirname(local_filename)
			if not os.path.exists(local_dirname):
				# This may fail if another thread creates.
				try:
					os.makedirs(local_dirname)
				except OSError, e:
					if e.errno != errno.EEXIST:
						raise
	
			# Save the file without there every being a partial tile written with the final name.
			cachefile = SaveAtomically(local_filename)
			try:
				cachefile.write(response.read())
			except socket.timeout:		# FIXME: socket is sometimes None. Why?
				self.feedback.debug(1, "  %s/%d/%d/%d: Socket timeout" % debug_args)
				self.feedback.error(_("Timeout during download"))
				self.conn = None		# close
				return False
			try:
				cachefile.close()
			except OSError, e:
				print "FIXME: OSError: %d" % e.errno

			modified = True
	
		# Tell the tile layer that the tile is ready so that it can redraw.
		if self.done_callback:
			try:
				self.done_callback(zoom, x, y, modified)
			except ReferenceError:
				self.feedback.debug(1, " Thread %s misses tile layer" % self.name)

		return True

class MapCacheCleaner(threading.Thread):
	def __init__(self, cache_root, scan_interval=30, max_age=180):
		threading.Thread.__init__(self, name="cache-cleaner")
		self.daemon = True
		self.cache_root = cache_root
		day = 24 * 60 * 60
		self.delete_if_before = time.time() - max_age * day
		self.scan_if_before = time.time() - scan_interval * day
		self.directory_delay = 0.2
		self.tileset_delay = 1200
	def run(self):
		time.sleep(5)		# wait until after startup
		print "Cache cleaner: starting"
		for tileset in os.listdir(self.cache_root):
			touchfile = os.path.join(self.cache_root, tileset, ".last-cleaned")
			if os.path.exists(touchfile):
				statbuf = os.stat(touchfile)
				if not statbuf.st_mtime < self.scan_if_before:
					print "Cache cleaner: %s cleaned too recently" % tileset
					continue
				else:
					# will try to remove directory
					os.unlink(touchfile)
			print "Cache cleaner: cleaning %s..." % tileset
			total = 0
			deleted = 0
			for dirpath, dirnames, filenames in os.walk(os.path.join(self.cache_root, tileset), topdown=False):
				for filename in filenames:
					path = os.path.join(dirpath, filename)
					statbuf = os.stat(path)
					if statbuf.st_atime < self.delete_if_before:
						deleted += 1
						os.unlink(path)
					total += 1
				self.rmdir(dirpath)
				time.sleep(self.directory_delay)
			# The whole cache may now be empty.
			if not self.rmdir(dirpath):
				# Nope, not empty. Note that we have cleaned it.
				open(touchfile, "w")
			print "Cache cleaner: %d of %d tiles removed from %s" % (deleted, total, tileset)
			time.sleep(self.tileset_delay)
		print "Cache cleaner: finished"

	def rmdir(self, dirpath):
		try:
			os.rmdir(dirpath)
			return True
		except OSError:
			return False

# Substitute for MapTileDownloader() for use when the map is in offline mode.
class MapTileCacheLoader(object):
	def __init__(self, tileset, tile_cache_basedir, feedback=None):
		self.tileset = tileset
		self.tile_cache_basedir = tile_cache_basedir
		self.feedback = feedback

	def load_tile(self, zoom, x, y, may_download):
		self.feedback.debug(1, "Load tile %s %d/%d/%d" % (self.tileset.key, zoom, x, y))
		local_filename = "%s/%s/%d/%d/%d" % (self.tile_cache_basedir, self.tileset.key, zoom, x, y)
		if os.path.exists(local_filename):
			return (local_filename, False)
		else:
			return (None, False)

#=============================================================================
# Mbtiles tile layer
# http://mapbox.com/developers/mbtiles/
#=============================================================================
class MapTileLayerMbtiles(MapTileLayer):
	def __init__(self, mbtiles_filename):
		MapTileLayer.__init__(self)
		import sqlite3
		self.conn = sqlite3.connect(mbtiles_filename)
		self.cursor = self.conn.cursor()
		self.zoom_min = int(self.fetch_metadata_item('minzoom', 0))
		self.zoom_max = int(self.fetch_metadata_item('maxzoom', 99))
		self.opacity = 1.0	
		self.attribution = self.fetch_metadata_item('attribution', '')

	def fetch_metadata_item(self, name, default):
		self.cursor.execute("select value from metadata where name = ?", (name,))
		result = self.cursor.fetchone()
		if result is not None:
			print "%s=%s" % (name, result[0])
			return result[0]
		else:
			return default

	# Return the indicated tile as a Cairo surface or None.
	def load_tile(self, zoom, x, y, may_download):
		y = (2**zoom-1) - y
		self.cursor.execute("select tile_data from tiles where zoom_level = ? and tile_column = ? and tile_row = ?", (zoom, x, y))
		result = self.cursor.fetchone()
		if result != None:
			try:
				return surface_from_file_data(result[0])
			except:
				pass
		return None

#=============================================================================
# Experimental layer which exports a map in SVG format from openstreetmap.org
# This is intended for printing.
#=============================================================================
class MapLayerSVG(MapLayer):
	def __init__(self, source, extra_zoom=1.0):
		if source != "osm-default-svg":
			raise ValueError

		MapLayer.__init__(self)
		self.source = source
		self.extra_zoom = extra_zoom
		self.attribution = u"Map © OpenStreetMap contributors"

		self.svg = None
		self.svg_scale = None

	def set_map(self, containing_map):
		MapLayer.set_map(self, containing_map)
		self.cache_dir = os.path.join(self.containing_map.tile_cache_basedir, self.source)
		if not os.path.exists(self.cache_dir):
			os.makedirs(self.cache_dir)

	def do_viewport(self):
		print "SVG layer: new viewport"
		bbox = self.containing_map.get_bbox()
		zoom = self.containing_map.get_zoom()

		# What a reading of http://svn.openstreetmap.org/applications/rendering/mapnik/zoom-to-scale.txt suggests:
		#scale = int(559082264.028 / math.pow(2, zoom) / self.extra_zoom + 0.5)

		# Determined by trial and error, produces map with expected pixel size
		scale = int(698000000 / math.pow(2, zoom) / self.extra_zoom + 0.5)

		print "SVG layer: scale:", scale
		cachefile = os.path.join(self.cache_dir, "%f_%f_%f_%f_%d.svg" % (bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat, scale))
		cachefile_age = file_age_in_days(cachefile)

		if cachefile_age is None or cachefile_age > 30:
			self.containing_map.feedback.progress(0, 2, _("Requesting SVG file"))

			url = "http://parent.tile.openstreetmap.org/cgi-bin/export?bbox=%f,%f,%f,%f&scale=%d&format=svg" % (bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat, scale)
			response = simple_urlopen(url)

			print "content-type:", response.getheader("content-type")
			content_length = int(response.getheader("content-length"))
			print "content-length:", content_length

			fh = SaveAtomically(cachefile)
			count = 0
			while True:
				self.containing_map.feedback.progress(float(count) / float(content_length), 2, _("Downloading SVG file"))
				data = response.read(0x10000)
				if data == "":
					break
				fh.write(data)
				count += len(data)
			fh.close()

		self.svg = rsvg.Handle(cachefile)
		if not self.svg:
			raise AssertionError("Failed to load SVG file: %s" % cachefile)

		print "SVG layer: map dimensions:", self.containing_map.width, self.containing_map.height
		width, height = self.svg.get_dimension_data()[:2]
		print "SVG layer: SVG image dimensions:", width, height
		self.svg_scale = float(self.containing_map.width) / float(width)
		print "SVG layer: svg_scale:", self.svg_scale

	def do_draw(self, ctx):
		self.containing_map.feedback.progress(1, 2, _("Rendering SVG file"))
		ctx.scale(self.svg_scale, self.svg_scale)
		self.svg.render_cairo(ctx)

#=============================================================================
# On Screen Display layers
#=============================================================================

class MapLayerCropbox(MapLayer):
	def __init__(self):
		MapLayer.__init__(self)
		self.cropbox = None

	def set_cropbox(self, cropbox):
		self.cropbox = cropbox
		self.containing_map.queue_draw()

	def get_cropbox(self):
		return self.cropbox

	def do_draw(self, ctx):
		# width, height, margin
		if self.cropbox:
			center_x = self.containing_map.width / 2
			center_y = self.containing_map.height / 2
			half_width = self.cropbox[0] / 2 - self.cropbox[2]
			half_height = self.cropbox[1] / 2 - self.cropbox[2]
	
			# Top
			ctx.move_to(center_x - half_width - 25, center_y - half_height)
			ctx.line_to(center_x + half_width + 25, center_y - half_height)
	
			# Bottom
			ctx.move_to(center_x - half_width - 25, center_y + half_height)
			ctx.line_to(center_x + half_width + 25, center_y + half_height)
	
			# Left
			ctx.move_to(center_x - half_width, center_y - half_height - 25)
			ctx.line_to(center_x - half_width, center_y + half_height + 25)
	
			# Right
			ctx.move_to(center_x + half_width, center_y - half_height - 25)
			ctx.line_to(center_x + half_width, center_y + half_height + 25)
	
			ctx.set_source_rgb(0.0, 0.0, 0.0)
			ctx.set_line_width(1)
			ctx.stroke()

class MapLayerScale(MapLayer):
	def __init__(self):
		MapLayer.__init__(self)
		self.scale_width_min = 100
		self.scale_width_max = 300
		self.scale_width_percentage = 15
		self.scale_dimensions = None

	# Compute the dimensions for the scale indicator.
	def do_viewport(self):
		#print "Adjusting map scale indicator"
		bbox = self.containing_map.get_bbox()

		scale_width = self.containing_map.width * self.scale_width_percentage / 100
		scale_width = max(self.scale_width_min, scale_width)
		scale_width = min(self.scale_width_max, scale_width)

		# How many meters are in 180 degrees of longitude at the latitude at the center of the map?
		half_parallel_in_meters = radius_of_earth * math.pi * math.cos(math.radians(self.containing_map.lat))

		# Knowing that we can compute the width in meters of area shown in the viewport.
		viewport_width_in_meters = (bbox.max_lon - bbox.min_lon) / 180.0 * half_parallel_in_meters

		# How many meters will fit in max_width pixels?
		max_meters = viewport_width_in_meters * (float(scale_width) / float(self.containing_map.width))

		# How may digits do we have to take off to get a one digit number?
		trailing_zeros = int(math.log10(max_meters))

		# What is the maximum value of the first digit?
		first_digit_max = max_meters / math.pow(10, trailing_zeros)

		# How may pixels will each tick of the first digit cover?
		first_digit_pixels = scale_width / first_digit_max

		if trailing_zeros == 0:
			units = "meters"
		elif trailing_zeros < 3:
			units = "1" + "0" * trailing_zeros + "x meters"
		else:
			trailing_zeros -= 3
			if trailing_zeros == 0:
				units = "kilometers"
			else:
				units = "1" + "0" * trailing_zeros + "x kilometers"

		self.scale_dimensions = (scale_width, first_digit_pixels, int(first_digit_max), units)

	def do_draw(self, ctx):
		#print "Drawing map scale:", self.scale_dimensions
		(scale_width, first_digit_pixels, first_digit_max, units) = self.scale_dimensions

		# Bottom right
		ctx.translate(self.containing_map.width - scale_width - 10, self.containing_map.height - 25)

		# Draw scale
		ctx.move_to(0, 0)						# base line
		ctx.line_to(scale_width, 0)
		for i in range(0, first_digit_max+1):	# ticks
			x = i * first_digit_pixels
			ctx.move_to(x, 0)
			ctx.line_to(x, -10)
		ctx.set_line_cap(cairo.LINE_CAP_ROUND)
		ctx.set_line_width(3)
		ctx.set_source_rgb(1.0, 1.0, 1.0)
		ctx.stroke_preserve()
		ctx.set_line_width(1)
		ctx.set_source_rgb(0.0, 0.0, 0.0)
		ctx.stroke()

		# Tick labels
		ctx.select_font_face("sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
		ctx.set_font_size(8)
		for i in range(0, first_digit_max+1):
			x = i * first_digit_pixels
			ctx.move_to(x-3, 9)
			ctx.text_path(str(i))

		# Description of units
		ctx.set_font_size(10)
		ctx.move_to(-3, 17)
		ctx.text_path(units)

		ctx.set_line_width(2)
		ctx.set_source_rgb(1.0, 1.0, 1.0)	# white halo
		ctx.stroke_preserve()
		ctx.set_source_rgb(0.0, 0.0, 0.0)	# black letters
		ctx.fill()

class MapLayerAttribution(MapLayer):
	def do_draw(self, ctx):
		x = 5
		y = self.containing_map.height - 5
		ctx.select_font_face("sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
		ctx.set_font_size(8)
		ctx.set_source_rgb(0.0, 0.0, 0.0)
		printed = set([])
		for layer in self.containing_map.layers_ordered:
			attribution = layer.attribution
			if attribution and attribution not in printed:
				ctx.move_to(x, y)
				ctx.text_path(attribution)
				ctx.set_line_width(1.5)
				ctx.set_source_rgb(1.0, 1.0, 1.0)	# white halo
				ctx.stroke_preserve()
				ctx.set_source_rgb(0.0, 0.0, 0.0)	# black letters
				ctx.fill()

				printed.add(attribution)
				y -= 10

#========================================================================
# Live GPS position layer
#========================================================================

class MapLayerLiveGPS(MapLayer):
	def __init__(self):
		MapLayer.__init__(self)
		self.marker_radius = 10

		self.fix = None
		self.screen_gps_pos = None
		self.screen_gps_arrow = None
		self.onscreen = False

	# Set the position, orientation, etc. of the GPS marker.
	# In order to prevent excessive redraws, we accept the position only if at
	# least one of the following conditions is met:
	# * The position difference is at least one pixel
	# * The bearing differs by at least five degrees
	# * The length of the speed indicator will differ by at least one pixel
	def set_marker(self, fix):
		pos_threshold = 360.0 / 256.0 / (2.0 ** self.containing_map.get_zoom())
		if fix is None or self.fix is None \
				or abs(fix.lat - self.fix.lat) >= pos_threshold \
				or (abs(fix.lon - self.fix.lon) % 360.0) >= pos_threshold \
				or (fix.heading is None != self.fix.heading is None) \
				or (abs(fix.heading - self.fix.heading) % 360.0) >= 5.0 \
				or abs(fix.speed - self.fix.speed) >= 1.0:
			print "GPS marker moved"
			self.fix = fix

			# If the marker is in the viewport (or just was), refresh layer.
			now_onscreen = self.containing_map.get_bbox().contains_point(Point(fix.lat, fix.lon)) if fix else False
			if now_onscreen or self.onscreen:
				self.set_stale()
			self.onscreen = now_onscreen

	# This is called whenever the map viewport changes.
	def do_viewport(self):
		self.screen_gps_pos = None
		self.screen_gps_arrow = None
		# If GPSd has reported a result which includes location, find
		# the cooresponding pixel position on the canvas.
		if self.fix:
			self.screen_gps_pos = self.containing_map.project_point(Point(self.fix.lat, self.fix.lon))
			# If a heading was reported, prepare to draw a vector.
			if self.fix.heading is not None:
				heading = math.radians(self.fix.heading)
				# If the speed is known, make the vector proportionally longer.
				if self.fix.speed:
					arrow_length = self.marker_radius + self.fix.speed
				else:
					arrow_length = self.marker_radius
				x, y = self.screen_gps_pos
				self.screen_gps_arrow = (
					x + arrow_length * math.sin(heading),
					y - arrow_length * math.cos(heading)
					)

	# Draw or redraw layer
	def do_draw(self, ctx):
		if self.screen_gps_pos:
			x, y = self.screen_gps_pos
			ctx.arc(x, y, self.marker_radius, 0, 2*math.pi)
			ctx.set_line_width(1)
			ctx.set_source_rgb(0.0, 0.0, 0.0)
			ctx.stroke_preserve()
			ctx.set_source_rgba(0.0, 0.0, 1.0, 0.5)
			ctx.fill()

			if self.screen_gps_arrow:
				ctx.move_to(x, y)
				ctx.line_to(*self.screen_gps_arrow)
				ctx.set_line_width(2)
				ctx.set_source_rgb(0.0, 0.0, 0.0)
				ctx.stroke()

