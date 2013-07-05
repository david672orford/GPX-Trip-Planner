# coding=utf-8
#=============================================================================
# gpx_gui.py
# Copyright 2013, Trinity College
# Last modified: 25 June 2013
#=============================================================================

import sys
import os
import gtk
import math
import glob
import re
import gettext
import traceback
import datetime
import codecs
import subprocess
import fnmatch

import utils_updater
from utils_gtk_appbusy import AppBusy
from utils_svg_icons import load_icon_pixbuf
import utils_gtk_macosx
from utils_gtk_entry import text_entry_wrapper
import lib.format_csv_unicode as csv

import pykarta.geometry
import pykarta.maps.tilesets
from pykarta.maps.widget import MapWidget, MapPrint
from pykarta.maps.layers import MapLayerScale, MapLayerAttribution, MapLayerCropbox, MapLayerLiveGPS
from pykarta.gps.live import GPSlistener

import gpx_reference_layers
import gpx_colors

from gpx_data_gpx import GpxData, GpxWriter, GpxWaypoint, GpxRoute, GpxRoutePoint, GpxMetadata
from gpx_data_pois import PoiDB
from gpx_data_search import search_nominatim, SearchMatches
from gpx_data_photos import GpxPhotos

from gpx_layer_waypoints import WaypointLayer
from gpx_layer_routes import RouteLayer
from gpx_layer_tracks import TrackLayer
from gpx_layer_search import SearchLayer
from gpx_layer_pois import PoiLayer
from gpx_layer_photos import PhotoLayer
import pykarta.maps.layers.mapquest

from gpx_router_mapquest import GpxRouter
#from gpx_router_osrm import GpxRouter

from gpx_satnavs import GpxSatnavs
import gpx_josm

#=============================================================================
# Treeviews for sidebar
#=============================================================================

# This basic version just handles selection. The treeview's renderers
# are expected to select the data in the usual way.
class GpxSimpleTreeView(object):
	def __init__(self, builder, stem, data):
		print "TreeView:", stem

		self.treeview = builder.get_object("tv_%s" % stem)
		self.data = data
		self.data.add_client('treeview', self)

		self.selection = self.treeview.get_selection()
		self.signal_enabled = True
		self.selection.connect("changed", self.selection_changed_cb)
		self.treeview.connect("row-activated", self.row_activated_cb)

		self.treeview.set_model(self.data.datastore)

	# Selection changed by means of a different widget
	def on_select(self, path, source, client_name):
		if path != None:
			self.treeview.expand_to_path(path)
			self.treeview.scroll_to_cell(path, column=None, use_align=True, row_align=0.5, col_align=0.0)
		self.signal_enabled = False
		self.selection.unselect_all()
		if path != None:
			self.selection.select_path(path)
		self.signal_enabled = True

	# Callback from Treeview widget for when the user selects a different row.
	def selection_changed_cb(self, widget, data=None):
		if self.signal_enabled:		# if not a result of calling select(),
			model, paths = self.selection.get_selected_rows()

			# If something is now selected,
			if paths:
				# If a subordinate object was selected, make sure
				# its parent is shown on the map
				if len(paths[0]) > 1:
					self.data[paths[0][0]].gpxtp_show = True

				# Inform the datastore so it can inform the other
				# controls which display this data.
				self.data.select(paths[0], 'treeview')

	# Callback from Treeview widget for when user double clicks on a row.
	def row_activated_cb(self, treeview, path, view_column):
		self.data.select(path, 'treeview_double_click')

# This adds:
# * Extraction of data from a Python object in the first column
# * Visibility checkboxes
# * Row reordering
class GpxFancyTreeView(GpxSimpleTreeView):
	def __init__(self, builder, stem, data, fields, map_obj):
		GpxSimpleTreeView.__init__(self, builder, stem, data)
		self.map_obj = map_obj

		self.show_all = True

		self.treeview.connect("drag-motion", self.drag_motion_cb)

		for field in fields:
			print "  tv_%s_%s" % (stem, field)
			column = builder.get_object("tv_%s_%s" % (stem, field))
			renderer = builder.get_object("tv_%s_%s_renderer" % (stem, field))
			column.set_cell_data_func(renderer, self.cell_data_cb, field)

		# Checkbox
		column = builder.get_object("tv_%s_show" % stem)
		if column:
			renderer = builder.get_object("tv_%s_show_renderer" % stem)
			column.set_cell_data_func(renderer, self.show_pixmap_cb)
			self.treeview.connect("button-press-event", self.button_press_cb)
			column.connect("clicked", self.header_clicked_cb)

			self.show_yes = load_icon_pixbuf("show_yes.svg")
			self.show_no  = load_icon_pixbuf("show_no.svg")
			image = gtk.Image()
			image.set_from_pixbuf(load_icon_pixbuf("show_header.svg"))
			column.set_widget(image)
			image.show()

	# Called by Treeview. Extracts data to be displayed from
	# the python object in column 0.
	def cell_data_cb(self, column, cell_renderer, tree_model, iter, field):
		python_obj = tree_model.get_value(iter, 0)

		try:		# not all objects in the heirarcy will have all fields
			if field == 'coords':
				value = "%.4f,%.4f" % (python_obj.lat, python_obj.lon)
			else:
				value = getattr(python_obj, field)
		except AttributeError as e:
			value = None

		if field == 'sym':
			symbol = self.map_obj.symbols.get_symbol(value, None)
			cell_renderer.set_property('pixbuf', symbol.get_pixbuf() if symbol else None)
		else:
			cell_renderer.set_property('text', value)

	# Called by Treeview. Selects the correct image for the column which 
	# indicates whether the a compound object (such as a route or a track)
	# should be displayed on the map.
	def show_pixmap_cb(self, column, cell_renderer, tree_model, iter):
		python_obj = tree_model.get_value(iter, 0)
		try:
			if python_obj.gpxtp_show:
				pixbuf = self.show_yes
			else:
				pixbuf = self.show_no
		except AttributeError:
			pixbuf = None
		cell_renderer.set_property('pixbuf', pixbuf)

	# Called when the user clicks on the treeview column header of the checkmark column
	def header_clicked_cb(self, treeviewcolumn):
		print "Show (or unshow) all"
		self.show_all = not self.show_all
		i = 0
		for obj in self.data:
			if obj.gpxtp_show != self.show_all:
				obj.gpxtp_show = self.show_all
				self.data.touch((i,))
			i += 1

	# We use this to detect clicks on the image provided by pixmap_cb().
	def button_press_cb(self, treeview, gdkevent):
		if gdkevent.type == gtk.gdk.BUTTON_PRESS and gdkevent.button == 1:
			result = treeview.get_path_at_pos(int(gdkevent.x), int(gdkevent.y))
			if result != None:	# if click hit a table cell,
				path, column, cell_x, cell_y = result
				if column == treeview.get_column(0):	# if click is on left column,
					print "Click:", path, gdkevent.type
					if len(path) == 1:
						self.data[path[0]].gpxtp_show = not self.data[path[0]].gpxtp_show
						self.data.touch(path[:1])
						return True
		return False

	# Called whenever a dragged row is hovering over the treeview.
	# This serves as a filter which allows only valid movements
	# of treestore rows. A valid movement is one that does not alter
	# the depth of the row. Without this, we could drag a route into
	# a route or drag a route point into the root.
	#
	# Returning True approves the transfer, False forbids it.
	#
	# Drag-and-drop is poorly documented. These code examples were helpful:
	# * http://pydoc.net/takenote/0.4/takenote.gui.treemodel
	# * http://stackoverflow.com/questions/2209650/in-gtk-when-using-drag-and-drop-in-a-treeview-how-do-i-keep-from-dropping-betw
	def drag_motion_cb(self, treeview, context, x, y, etime):

		# Prevent default handler from firing after this one?
		treeview.stop_emission("drag-motion")

		# Find the source widget and make sure this is an intra-widget drag.
		source_widget = context.get_source_widget()
		if source_widget != treeview:
			return False

		# Find the location within the widget where the dragged selection is hovering.
		# The examples test for None. Perhaps there are locations within the treeview
		# that are not valid targets.
		destination = treeview.get_dest_row_at_pos(x, y)
		if not destination:
			return False

		# Find the selection (which is what is being dragged).
		selection = self.selection.get_selected_rows()
		source_path = selection[1][0]
	
		dest_path, dest_relative = destination
		print "Drag from", source_path, "to", dest_path, "(", dest_relative, ")"

		# Approve if:
		# * the row's path has fewer then three levels (track points are not draggable)
		# * the source and destination paths have the same number of levels (the rows are peers)
		# * the user proposes to drop the row before or after (but not on) its peer)
		# Exception:
		# * An object may be dropt into an object one level above it
		if len(source_path) < 3 and (
				(len(source_path) == len(dest_path) and (dest_relative == gtk.TREE_VIEW_DROP_BEFORE or dest_relative == gtk.TREE_VIEW_DROP_AFTER))
					or
				((len(source_path) - len(dest_path)) == 1 and (dest_relative == gtk.TREE_VIEW_DROP_INTO_OR_BEFORE or dest_relative == gtk.TREE_VIEW_DROP_INTO_OR_AFTER))
				):
			print "  Approved!"
			# This highlights the target location.
			treeview.set_drag_dest_row(dest_path, dest_relative)
			context.drag_status(context.suggested_action, etime)
			# This indicates our approval of the possible transfer.
			return True

		return False

#=============================================================================
# Form for Sidebar
#=============================================================================

class GpxForm(object):
	def __init__(self, builder, mapsym_chooser, stem, fields, gpx_data_subset):
		print "Form:", stem
		self.mapsym_chooser = mapsym_chooser	# Dialog for choosing POI symbol
		self.data = gpx_data_subset
		self.data.add_client('form', self)
		self._selected = None

		# Find the form entries from the Glade file.
		self.field_entries = []
		for field_name in fields:
			print "  form_%s_%s" % (stem, field_name)
			widget = text_entry_wrapper(builder.get_object("form_%s_%s" % (stem, field_name)))

			if field_name == 'link':
				widget.connect('clicked', self.link_clicked_cb)
			elif widget.get_editable():	# lat, lon may not be directly editable
				widget.connect('changed', self.entry_changed_cb, field_name)

			# The sym field has a button next to it which pops up a chooser window.
			if field_name == "sym":
				button = builder.get_object("form_%s_%s_chooser" % (stem, field_name))
				button.connect("clicked", self.choose_sym_button_cb, widget)

			self.field_entries.append([field_name, widget])

		# Routes and tracks have settable color.
		self.color_selector = builder.get_object("form_%s_display_color" % stem)
		if self.color_selector:
			self.color_selector.set_model(gpx_colors.liststore)
			self.color_selector.connect("changed", self.display_color_changed_cb)
			self.color_show = [
				builder.get_object("form_%s_display_color_label" % stem),
				builder.get_object("form_%s_display_color" % stem),
				]
			self.color_hide = [
				builder.get_object("form_%s_coords_label" % stem),
				builder.get_object("form_%s_coords" % stem),
				]

		self.signal_enabled = True

	# Called when the contents of a gtk.Entry or gtk.TextView changes
	def entry_changed_cb(self, widget, field_name):
		if self.signal_enabled:
			if self._selected is not None:
				obj = self.data[self._selected]
				value = widget.get_text()
				if field_name == "lat" or field_name == "lon":
					value = float(value)
				setattr(obj, field_name, value)	
				self.data.touch(self._selected)
			else:
				print "Form is empty"
				gtk.gdk.beep()
				widget.set_text("")

	def display_color_changed_cb(self, widget):
		if self.signal_enabled:
			if self._selected != None and len(self._selected) == 1:
				color = gpx_colors.colors[widget.get_active()][0]
				print "Display color changed:", color
				obj = self.data[self._selected]
				obj.gpxx_DisplayColor = color
				self.data.touch(self._selected)

	# The selection has changed. If path is None, clear the form. Otherwise,
	# retrieve the indicated object and load its data into the form.
	def on_select(self, path, source, client_name):
		self._selected = path

		self.signal_enabled = False		# prevent loops

		obj = self.data[path] if path != None else None
		for i in self.field_entries:
			field_name, widget = i
			if field_name == 'link':
				label = ""
				uri = ""
				if obj and obj.link:
					if obj.link.href:
						uri = obj.link.href
					if obj.link.text:
						label = obj.link.text
					else:
						label = uri
				widget.set_label(label)
				widget.set_uri(uri)
			else:
				if obj and hasattr(obj, field_name):
					widget.set_text(str(getattr(obj, field_name)))
				else:
					widget.set_text("")

		if self.color_selector:
			color_index = -1
			if path != None and len(path) == 1:
				color = self.data[path].gpxx_DisplayColor
				#print "Color of selected route:", color
				color_index = gpx_colors.index_by_name.get(color, -1) if color != None else -1
				self.color_selector.set_active(color_index)
				to_show = self.color_show
				to_hide = self.color_hide
			else:
				to_show = self.color_hide
				to_hide = self.color_show
			for widget in to_show:
				widget.show()
			for widget in to_hide:
				widget.hide()

		self.signal_enabled = True

	# Button next to Symbol entry
	def choose_sym_button_cb(self, widget, entry):
		answer = self.mapsym_chooser.choose()
		if answer:
			entry.set_text(answer)

	# The form can have a row of buttons each of which sets the "type" to
	# a particular value.
	def set_type_button_cb(self, widget, type_name):
		self.type_entry.set_text(type_name)

	# Called when a button which represents a <link> tag is clicked.
	def link_clicked_cb(self, widget):
		uri = widget.get_uri()
		print "Link clicked:", uri
		# Disabled because Gtk+ handles this by default.
		#if uri:
		#	subprocess.Popen(["xdg-open", uri])
		return True

#=============================================================================
# Wrapper for sidebar controls for taking selected object and making
# a new waypoint or route point of it
#=============================================================================

class GpxPicker(object):
	def __init__(self, builder, stem, data_from, data, point_depth, syncer):
		print "Picker:", stem

		self.data_from = data_from		# source data store
		data_from.add_client('picker', self)
		self.data = data				# general waypoints, routes, tracks data store
		self.point_depth = point_depth	# path point_depth of pickable rows

		self.path = None

		self.add_wp_button = builder.get_object("%s_waypoints_add_button" % stem)
		if self.add_wp_button:
			print "  wp add"
			self.add_wp_button.connect('clicked', self.add_wp_button_cb)
			self.add_wp_button.set_sensitive(False)

		self.add_rp_button = builder.get_object("%s_route_add_button" % stem)
		if self.add_rp_button:
			print "  rp add"
			self.add_rp_button.connect('clicked', self.add_rp_button_cb)
			self.add_rp_button.set_sensitive(False)

			self.add_rp_list = builder.get_object("%s_route_add_list" % stem)
			self.add_rp_list.set_model(self.data.routes.picklist)
			self.add_rp_list.set_sensitive(False)
			syncer.add(self.add_rp_list.child)

		self.reset()

	def reset(self):
		if self.add_rp_button:
			self.add_rp_list.set_active(0)

	# Selection changed
	def on_select(self, path, source, client_name):
		self.path = path

		# Is there a pickable point?
		enable = (path != None and len(path) == self.point_depth)
		if self.add_wp_button:
			self.add_wp_button.set_sensitive(enable)
		if self.add_rp_button:
			self.add_rp_button.set_sensitive(enable)
			self.add_rp_list.set_sensitive(enable)

	# Button "Add to Waypoints" pressed
	def add_wp_button_cb(self, widget):
		print "Add waypoint"
		# Clone the point and add it.
		wpt = GpxWaypoint(self.data_from[self.path])
		self.data.waypoints.append(wpt)
		self.data.waypoints.select((len(self.data.waypoints)-1,), "picker")

	# Button "Add to a Route" pressed
	def add_rp_button_cb(self, widget):
		route_name = self.add_rp_list.child.get_text()
		print "Add point to route", route_name
		route = None

		# Find the last route with the specified name
		for i in reversed(self.data.routes):
			if i.name == route_name:
				route = i
				break

		# If named route not found, create it.
		if route == None:
			route = GpxRoute()
			route.name = route_name
			self.data.routes.append(route)

		# Clone the point and add it.
		rtept = GpxRoutePoint(self.data_from[self.path])
		route.append(rtept)
		self.data.routes.select((len(self.data.routes)-1,), "picker")

# This keeps two or more gtk.Entry widgets in sync.
class GpxEntrySyncer(object):
	def __init__(self):
		self.active = False
		self.widgets = []

	def add(self, widget):
		self.widgets.append(widget)
		widget.connect('changed', self.changed_cb)

	def changed_cb(self, changed_widget, data=None):
		if not self.active:
			self.active = True
			text = changed_widget.get_text()
			for widget in self.widgets:
				if widget != changed_widget:
					widget.set_text(text)
			self.active = False
		
#=============================================================================
# Map Symbol Chooser
#=============================================================================

class MapSymbolChooser(object):
	def __init__(self, builder, map):
		self.builder = builder
		self.map = map
		self.loaded = False

	def choose(self):
		if not self.loaded:
			self.dialog = self.builder.get_object("MapSymbolDialog")

			self.iconview = self.builder.get_object("MapSymbolDialogIconview")
			self.iconview.connect('item-activated', self.double_click)

			self.sym_store = self.builder.get_object("MapSymbols")
			for sym in self.map.symbols.get_symbol_pixbufs():
				self.sym_store.append(sym)
			self.loaded = True

		answer = self.dialog.run()
		self.dialog.hide()

		if answer != 1:		# 1 is OK
			return None

		selected = self.iconview.get_selected_items()
		if len(selected) < 1:
			return None

		return self.sym_store[selected[0][0]][0]

	def double_click(self, widget, path):
		print "Double click:", path
		self.dialog.response(1)

#=============================================================================
# Image Display Area
#=============================================================================
class GpxImage(object):
	def __init__(self, builder, stem, data):
		self.data = data
		self.image = builder.get_object("%s_image" % stem)
		self.filename = None
		data.add_client("%s_image" % stem, self)
		# FIXME: should detect clicks, not just button down
		builder.get_object("photo_image_eventbox").connect('button-press-event', self.clicked_cb)
	def on_select(self, path, source, client_name):
		photo = self.data[path]
		self.load(photo.filename)
	def load(self, filename):
		self.filename = filename
		#self.image.set_from_file(filename)
		pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
		target_width = 360
		target_height = pixbuf.get_height() / (pixbuf.get_width() / target_width)
		scaled_pixbuf = pixbuf.scale_simple(target_width, target_height, gtk.gdk.INTERP_BILINEAR)
		self.image.set_from_pixbuf(scaled_pixbuf)
	def clicked_cb(self, widget, gdkevent):
		print "Photo clicked:", self.filename
		if self.filename:
			subprocess.Popen(["xdg-open", self.filename])

#=============================================================================
# Wrapper for Copy, Paste, Delete
# Also handles Send to GPSr
#=============================================================================

class GpxEditMenu(object):
	def __init__(self, builder, data, clipboard, search_cb, gpsr, ui, map):
		self.data = data
		self.layer_data = {
			'waypoint':data.waypoints,
			'route':data.routes,
			'track':data.tracks,
			}
		self.clipboard = clipboard
		self.search_cb = search_cb
		self.satnav = gpsr
		self.ui = ui
		self.map = map
		self.server = None

		self.active_layer_name = None
		self.layer_selections = {
			'waypoint':None,
			'route':None,
			'track':None,
			'search':None,		# always disabled
			'poi':None,
			'photo':None,
			}

		for layer_name, layer_data in self.layer_data.items():
			layer_data.add_client("edit_%s" % layer_name, self)

		self.menu_cut = builder.get_object("menu_edit_cut")
		self.menu_cut.connect("activate", self.on_cut)
		self.menu_copy = builder.get_object("menu_edit_copy")
		self.menu_copy.connect("activate", self.on_copy)
		self.menu_paste = builder.get_object("menu_edit_paste")
		self.menu_paste.connect("activate", self.on_paste)
		self.menu_delete = builder.get_object("menu_edit_delete")
		self.menu_delete.connect("activate", self.on_delete)
		self.menu_split = builder.get_object("menu_edit_split")
		self.menu_split.connect("activate", self.on_split)
		self.menu_sync_josm = builder.get_object("menu_edit_sync_josm")
		self.menu_sync_josm.connect("activate", self.on_sync_josm)
		self.menu_waypoint_to_josm = builder.get_object("menu_edit_waypoint_to_josm")
		self.menu_waypoint_to_josm.connect("activate", self.on_waypoint_to_josm)

		self.button_send_to_gpsr = builder.get_object("gpsr_send_to")
		self.button_send_to_gpsr.connect("clicked", self.on_send_to_gpsr)
		self.satnav_list = builder.get_object("gpsr_selector")
		self.satnav_list.set_model(self.satnav.liststore)

		self.update_sensitive()

	# We are informed when the active layer changes by a call to this function.
	def set_layer(self, layer_name):
		self.active_layer_name = layer_name
		self.update_sensitive()

	# We are informed when the section changes by a call to this function.
	def on_select(self, path, source, client_name):
		layer = client_name.split("_")[1]
		self.layer_selections[layer] = path
		self.update_sensitive()

	def update_sensitive(self):
		enable = self.active_layer_name != None and self.layer_selections[self.active_layer_name] != None
		self.menu_cut.set_sensitive(enable)
		self.menu_copy.set_sensitive(enable)
		self.menu_delete.set_sensitive(enable)
		self.menu_split.set_sensitive(enable and self.active_layer_name == 'track')
		self.menu_waypoint_to_josm.set_sensitive(enable and self.active_layer_name == 'waypoint')
		self.button_send_to_gpsr.set_sensitive(enable)

	def get_selected_obj(self):
		return self.layer_data[self.active_layer_name][self.layer_selections[self.active_layer_name]]

	def del_selected_obj(self):
		del self.layer_data[self.active_layer_name][self.layer_selections[self.active_layer_name]]

	def on_cut(self, widget):
		print "Edit->Cut"
		import StringIO
		fh = StringIO.StringIO()
		self.get_selected_obj().write(GpxWriter(fh))
		self.clipboard.set_text(fh.getvalue())
		self.clipboard.store()		# needed?
		self.del_selected_obj()

	def on_copy(self, widget):
		print "Edit->Copy"
		import StringIO
		fh = StringIO.StringIO()
		self.get_selected_obj().write(GpxWriter(fh))
		self.clipboard.set_text(fh.getvalue())
		self.clipboard.store()		# needed?

	def on_paste(self, widget):
		print "Edit->Paste"
		pasted_text = unicode(self.clipboard.wait_for_text())
		#print "Pasted text:", pasted_text

		if pasted_text is None:
			self.ui.error(_("The paste buffer is empty."))
			return

		if pasted_text.find("<gpx", 0, 100) >= 0:
			print "Pasted text is in GPX format"
			try:
				import StringIO
				fh = StringIO.StringIO(pasted_text)
				self.data.load_gpx(fh)
			except Exception as e:
				self.ui.error(_("Pasted text is not a valid GPX file."))
			return

		if pasted_text.startswith("http:") or pasted_text.startswith("https:"):
			print "Pasted text is a URL"
			import gpx_import_url
			mark = self.data.get_mark()
			gpx_import_url.load_url(pasted_text, self.data, self.ui)
			self.map.zoom_to_extent(self.data.get_bbox(mark=mark))
			return

		lat, lon = pykarta.geometry.parse_lat_lon(pasted_text)
		if lat is not None:
			print "Parsed:", lat, lon
			point = GpxWaypoint(lat, lon)
			point.name = pasted_text
			mark = self.data.get_mark()
			self.data.waypoints.append(point)
			self.map.zoom_to_extent(self.data.get_bbox(mark=mark))
			return

		if len(pasted_text) > 8192:
			self.ui.error(_("Pasted text is unreasonably long."))
			return

		print "Pasting to search:", pasted_text
		self.search_cb(pasted_text)

	def on_delete(self, widget):
		print "Edit->Delete"
		self.del_selected_obj()

	def on_split(self, widget):
		print "Edit->Split"
		self.layer_data[self.active_layer_name].split(self.layer_selections[self.active_layer_name])

	def on_sync_josm(self, widget):
		gpx_josm.sync_view_and_load(self.map.get_bbox())

	def on_waypoint_to_josm(self, widget):
		print "Edit->Send to JOSM"
		gpx_josm.add_obj(self.get_selected_obj(), self.ui, self.server)

	def on_send_to_gpsr(self, widget):
		print "Send to GPSr"
		gpsr_index = self.satnav_list.get_active()
		if gpsr_index == -1:
			self.ui.error("No GPSr selected.")
			return
		if self.satnav.send_obj(gpsr_index, self.get_selected_obj()):
			self.ui.show_status(_("Object sent to GPSr"))

#=============================================================================
# Wrapper for route operations in the Tools menu
#=============================================================================

class GpxRouteToolsMenu(object):

	def __init__(self, builder, route_data, appbusy_factory):
		self.menu_names = ["flesh_out_route", "pare_route", "strip_route", "reverse_route"]
		self.menus = {}
		self.selected = None

		for menu_name in self.menu_names:
			self.menus[menu_name] = builder.get_object("menu_tools_%s" % menu_name)
			self.menus[menu_name].connect("activate", getattr(self, "on_%s" % menu_name))
			self.menus[menu_name].set_sensitive(False)

		self.route_data = route_data
		self.route_data.add_client("tools_menu", self)

		self.appbusy_factory = appbusy_factory

	def on_select(self, path, sender, client_name):
		self.selected = path
		active = (path != None)
		for menu_name in self.menu_names:
			self.menus[menu_name].set_sensitive(active)

	def on_flesh_out_route(self, widget):
		print "Tools->Flesh out Route"
		saved_selected = self.selected
		route = self.route_data[self.selected[0]]		# takes route of selected point
		self.strip(route)
		router = GpxRouter()
		busy = self.appbusy_factory("Routing...")
		router.flesh_out(route)
		print "Route now has %d points" % len(route)
		self.route_data.select((saved_selected[0],), "tools_route")

	def on_pare_route(self, widget):
		print "Tools->Pare Route"
		saved_selected = self.selected
		route = self.route_data[self.selected[0]]
		i = 1
		while i < (len(route) - 1):
			point = route[i]
			next_point = route[i+1]
			if point.type == 'guide' and next_point.type == 'maneuver':
				next_point.type = 'guide'
				del route[i]
			i += 1
		self.route_data.select((saved_selected[0],), "tools_route")

	def on_strip_route(self, widget):
		print "Tools->Strip Route"
		saved_selected = self.selected
		route = self.route_data[self.selected[0]]
		self.strip(route)
		self.route_data.select((saved_selected[0],), "tools_route")

	def on_reverse_route(self, widget):
		print "Tools->Reverse Route"
		route = self.route_data[self.selected[0]]
		saved_selected = self.selected

		new_points = []
		prev_route_shape = []
		while len(route) > 0:			# pull out points and build reversed route
			point = route[0]
			del route[0]
			this_route_shape = point.route_shape
			print "shape:", prev_route_shape
			point.route_shape = list(reversed(prev_route_shape))
			prev_route_shape = this_route_shape
			new_points.insert(0, point)
		for point in new_points:		# push points from reversed route in
			route.append(point)

		self.route_data.select((saved_selected[0],), "tools_route")

	# Remove any points added by a previous run.
	def strip(self, route):
		i = 0
		while i < len(route):
			if route[i].type == 'maneuver':
				del route[i]
			else:
				route[i].route_shape = []
				i += 1

#==========================================================================
# UI elements which may be need by modules
#==========================================================================

class GpxPassableUI(object):
	def __init__(self, builder):
		self.builder = builder
		self.statusbar = self.builder.get_object("MainStatusbar")

	def yesno_question(self, question):
		dialog = self.builder.get_object("YesNoDialog")
		dialog.set_markup(question)
		answer = dialog.run()
		dialog.hide()
		if answer == -4:		# user clicked x on title bar
			return None
		elif answer:
			return True
		else:
			return False

	def error(self, message):
		dialog = self.builder.get_object("ErrorDialog")
		message = message.replace("&", "&amp;")
		message = message.replace("<", "&lt;")
		message = message.replace(">", "&gt;")
		dialog.set_markup(message)
		dialog.run()
		dialog.hide()

	def exception(self, operation, e):
		(e_type, e_value, e_traceback) = sys.exc_info()
		print "%s: %s" % (e_type, e_value)
		print traceback.format_exc(e_traceback)
		self.error("Failure during %s: %s" % (operation, str(e)))

	def show_status(self, status_text):
		self.statusbar.set_text(status_text)
		while gtk.events_pending():			# make sure message shows up right away
			gtk.main_iteration(False)

#=============================================================================
# Main
#=============================================================================

class GpxGUI(object):

	def __init__(self, profile_dir):
		self.profile_dir = profile_dir

		self.app_name = "GPX Trip Planner"
		self.bookmarks_filename = os.path.join(self.profile_dir, "bookmarks.csv")
		self.pois_db_filename = os.path.join(self.profile_dir, "POIs", "pois.sqlite")
		self.processed_tracks_dir = os.path.join(self.profile_dir, "Processed_Tracks")

		self.tool = None
		self.mode_signal_enabled = True
		self.package_updates = []
		self.loaded_tracks = set([])
		self.latlon_units = 'deg'
		self.save_filename = None

		# Must be done before Gtk+ is initialized
		self.macapp = utils_gtk_macosx.Application()

		#------------------------
		# Load GUI description
		#------------------------
		self.builder = gtk.Builder()
		self.builder.set_translation_domain(gettext.textdomain())
		self.builder.add_from_file(os.path.join(sys.path[0], "gpx_gui.xml"))
		self.builder.connect_signals(self)

		# Elements to which we will refer frequently
		self.main_window = self.builder.get_object("MainWindow")
		self.sidebar = self.builder.get_object("Sidebar")
		self.mode_selector = self.builder.get_object("ModeSelector")
		self.coordinates_display = self.builder.get_object("CoordinatesDisplay")
		self.zoom_display = self.builder.get_object("ZoomDisplay")

		# Routines which modules can use to make limited use of the UI
		self.ui = GpxPassableUI(self.builder)

		#---------------------------------------------------------
		# Set window manager hints
		#---------------------------------------------------------
		icon_list = []
		for size in (16, 32, 48, 64, 128):
			icon_list.append(gtk.gdk.pixbuf_new_from_file(os.path.join(sys.path[0], "images", "app_icon-%dx%d.png" % (size, size))))
		gtk.window_set_default_icon_list(*icon_list)

		#---------------------------------------------------------
		# Enlarge on large screens
		#---------------------------------------------------------
		if gtk.gdk.screen_height() >= 1024:
			self.main_window.set_default_size(1200, 800)

		#---------------------------------------------------------
		# Create data store
		#---------------------------------------------------------

		# The data store is a very important object. It not 
		# only stores the data, but it is the central hub through which
		# all communcation between the various views of the data such
		# as the map and the sidebar takes place.
		self.data = GpxData()

		#---------------------------------------------------------
		# GPS
		#---------------------------------------------------------

		# GPS navigators
		self.satnav = GpxSatnavs(self.ui)

		# Live GPS receiver
		self.live_gps_control = self.builder.get_object("live_gps_switch")
		self.live_gps_mode = 0
		self.live_gps_listener = None
		self.live_gps_trackseg = None

		#---------------------------------------------------------
		# Create the map widget
		#---------------------------------------------------------
		self.map = MapWidget(tile_source=None)
		self.builder.get_object("MapVbox").pack_end(self.map)
		self.map.set_coordinates_cb(self.coordinates_cb)
		self.map.set_zoom_cb(self.zoom_cb)
		self.map.set_size_request(300, 400)	# minimum size
		self.map.add_osd_layer(MapLayerScale())
		self.map.add_osd_layer(MapLayerAttribution())
		self.cropbox_layer = self.map.add_osd_layer(MapLayerCropbox())
		self.map.show()

		#---------------------------------------------------------
		# Load <sym> images
		#---------------------------------------------------------
		sym_dir = os.path.join(sys.path[0], "gpx_syms")
		for filename in glob.glob("%s/*/*.svg" % sym_dir):
			self.map.symbols.add_symbol(filename)

		self.mapsym_chooser = MapSymbolChooser(self.builder, self.map)

		#---------------------------------------------------------
		# This keeps all of the gtk.Entry widgets with the name
		# of the route to which points are being added showing
		# the same text.
		#---------------------------------------------------------
		self.route_name_syncer = GpxEntrySyncer()

		#------------------------
		# Waypoints Layer
		#------------------------

		# Map layer which displays data from self.data
		self.map.add_layer('waypoint', WaypointLayer(self.data))

		# Connect waypoint liststore to the treeview and form in the the left-hand pane.
		GpxFancyTreeView(self.builder, "waypoints", self.data.waypoints, ["sym", "name"], self.map)
		GpxForm(self.builder, self.mapsym_chooser, "waypoint", ["lat", "lon", "ele", "time", "name", "cmt", "desc", "src", "link", "sym", "type"], self.data.waypoints)

		# Connect waypoint picker
		self.first_picker = GpxPicker(self.builder, "waypoints", self.data.waypoints, self.data, 1, self.route_name_syncer)

		#------------------------
		# Routes Layer
		#------------------------

		self.map.add_layer('route', RouteLayer(self.data))

		GpxFancyTreeView(self.builder, "routes", self.data.routes, ["sym", "name"], self.map)
		GpxForm(self.builder, self.mapsym_chooser, "route", ["lat", "lon", "name", "cmt", "desc", "src", "sym", "type"], self.data.routes)

		GpxPicker(self.builder, "routes", self.data.routes, self.data, 2, self.route_name_syncer)

		#------------------------
		# Tracks Layer
		#------------------------

		self.map.add_layer('track', TrackLayer(self.data))

		GpxFancyTreeView(self.builder, "tracks", self.data.tracks, ["sym", "name", "coords"], self.map)
		GpxForm(self.builder, self.mapsym_chooser, "track", ["lat", "lon", "ele", "time", "name", "cmt", "desc", "src", "sym", "type"], self.data.tracks)

		GpxPicker(self.builder, "tracks", self.data.tracks, self.data, 3, self.route_name_syncer)

		#------------------------
		# Search
		#------------------------

		# Create storage area for search matches. Both the search results
		# treeview and the search results map layer will be connected to it.
		self.search_results = SearchMatches(map_obj=self.map)

		# Create Search map layer which will display the locations of the things found.
		search_layer = SearchLayer(self.search_results)
		self.map.add_layer('search', search_layer)

		# Connect the search results treeview in the sidebar to the search results storage.
		GpxSimpleTreeView(self.builder, "search_results", self.search_results)

		# Connect the search results picker
		GpxPicker(self.builder, "search", self.search_results, self.data, 1, self.route_name_syncer)

		#------------------------
		# POIs layer
		#------------------------
		poi_db = PoiDB(self.pois_db_filename)
		self.map.add_layer('poi', PoiLayer(poi_db))
		GpxFancyTreeView(self.builder, "pois", poi_db.categories, ["sym", "name", "desc"], self.map)
		GpxForm(self.builder, None, "poi", ["lat", "lon", "name", "desc", "link"], poi_db)
		GpxPicker(self.builder, "pois", poi_db, self.data, 1, self.route_name_syncer)

		#------------------------
		# Photos layer
		#------------------------
		self.photos = GpxPhotos()
		self.map.add_layer('photo', PhotoLayer(self.photos))
		GpxFancyTreeView(self.builder, "photos", self.photos, ["sym", "name", "desc"], self.map)
		GpxForm(self.builder, None, "photo", ["lat", "lon", "name", "desc"], self.photos)
		GpxImage(self.builder, "photo", self.photos)

		#------------------------
		# Live GPS layer
		#------------------------
		self.live_gps_layer = self.map.add_layer("GPS", MapLayerLiveGPS())

		#------------------------
		# Tile debuging layer
		#------------------------
		#self.map.add_layer('tile_debug', pykarta.maps.layers.MapTileLayerDebug())

		#---------------------------------------------------------
		# Main menu
		#---------------------------------------------------------

		# Initialize Edit menu Copy, Paste, and Delete
		# Also handles Send to GPSr
		self.edit_menu = GpxEditMenu(
			self.builder,
			self.data,
			gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD),
			self.edit_paste_search_cb,
			self.satnav,
			self.ui,
			self.map
			)
		# Tell it the waypoint layer is active as it soon will be
		self.edit_menu.set_layer("waypoint")

		# Create menu items for the map layers
		self.init_view_map_tiles()

		# Initialize Bookmarks menu
		self.init_bookmarks()

		# Initialize Tools menu
		self.tools_menu = GpxRouteToolsMenu(self.builder, self.data.routes, self.appbusy_factory)

		# Copy our menu to the MacOSX menu
		if self.macapp:
			utils_gtk_macosx.adjust_menus(self.macapp, self.builder, self.on_wm_close)
			self.macapp.ready()

		#------------------------
		# Final setup
		#------------------------

		# We must do this before zooming since we will not
		# know the size of our map until we do.
		self.main_window.show()

		# Waypoint layer starts on top
		self.map.raise_layer_to_top('waypoint')

		# Center map on the interesting part
		data_bbox = self.data.get_bbox()
		if data_bbox.valid:
			self.map.zoom_to_extent(data_bbox)
		else:
			self.map.set_center_and_zoom(42.125, -72.75, 10)

		# Tell it which tool is seleted at startup. This must be done after
		# the map widget is shown since it sets the cursor of the map widget.
		self.set_tool('tool_select')

	def set_server(self, server):
		self.edit_menu.server = server

	# Called whenever the tab in the sidebar is changed
	def on_sidebar_tab_changed(self, notebook, page, page_num):
		print "Tab:", page_num

		editing_layer = ("waypoint", "route", "track", "search", "poi", "photo")[page_num]

		self.map.raise_layer_to_top(editing_layer)
		self.set_tool(self.tool)
		self.edit_menu.set_layer(editing_layer)

		self.mode_signal_enabled = False
		self.mode_selector.set_active(page_num)
		self.mode_signal_enabled = True

	# Called whenever the GPS receiver switch is moved
	def live_gps_control_cb(self, widget):
		self.live_gps_mode = widget.get_active()
		if self.live_gps_mode == 0:
			if self.live_gps_listener:
				print "  Turning GPSr off..."
				self.live_gps_position_cb(None, None)	# clear coordinates
		elif self.live_gps_listener is None:
			try:
				self.live_gps_listener = GPSlistener(interface="gpsd", position_callback=self.live_gps_position_cb)
			except Exception as e:
				self.ui.error(_("Failed to start GPS: %s") % str(e))
				self.live_gps_control.set_active(0)

	# Receives fix objects from GPSd. Receives None if the user turns the GPSr switch off.
	def live_gps_position_cb(self, fix, error_detail):
		print "position fix:", fix
		self.live_gps_layer.set_marker(fix)
		if fix is not None:
			if self.live_gps_mode == 2:
				self.map.set_center_damped(fix.lat, fix.lon)
			if self.live_gps_trackseg is None:
				track_name = _("Track %s") % datetime.datetime.now().strftime("%Y-%m-%d")
				self.live_gps_trackseg = self.data.tracks.new_segment(track_name)
			self.live_gps_trackseg.append_fix(fix)
		else:
			if error_detail:
				self.ui.error(_("GPS failed: %s") % error_detail)
			self.live_gps_listener.close()
			self.live_gps_listener = None
			self.live_gps_trackseg = None
			self.live_gps_control.set_active(0)

	# Toolbar zoom buttons
	def on_zoom_in(self, widget):
		self.map.zoom_in()
	def on_zoom_out(self, widget):
		self.map.zoom_out()

	# Called whenever the drop-down interaction mode selector above the map
	# is changed. We keep its state synced with the state of the sidebar.
	def on_mode_selector_changed(self, widget):
		print "Interaction mode selector changed"
		if self.mode_signal_enabled:
			self.sidebar.set_current_page(widget.get_active())

	# Whenever a different tool is selected
	def on_toolbutton_toggled(self, widget):
		if widget.get_active():
			tool = gtk.Buildable.get_name(widget)
			if not self.set_tool(tool):
				gtk.gdk.beep()

	# Inform the active layer of the fact that the tool has been changed.
	def set_tool(self, tool):
		print "Tool:", tool
		self.tool = tool

		# Set the map cursor to match the tool
		if self.tool == "tool_adjust":
			self.map.set_cursor(gtk.gdk.Cursor(gtk.gdk.FLEUR))
		elif self.tool == "tool_draw":
			self.map.set_cursor(gtk.gdk.Cursor(gtk.gdk.PENCIL))
		elif self.tool == "tool_delete":
			self.map.set_cursor(gtk.gdk.Cursor(gtk.gdk.X_CURSOR))
		else:
			self.map.set_cursor(None)

		# Inform the active layer of the tool change. If it throws
		# an exception, press the button for tool_select.
		try:
			message = self.map.set_tool(self.tool)
			self.ui.show_status(message)
			return True
		except NotImplementedError:
			print "Layer rejected tool:", self.tool
			# Switch back to the Select tool
			self.builder.get_object("tool_select").set_active(True)
			return False

	# This is called repeatedly as the mouse pointer moves over the map.
	# It is called with a value of None when the mouse pointer leaves
	# the map.
	def coordinates_cb(self, point):
		if point:
			if self.latlon_units == "deg":
				self.coordinates_display.set_text("(%f, %f)" % point)
			elif self.latlon_units == "dms":
				self.coordinates_display.set_text("(%s, %s)" % pykarta.geometry.dms_lat_lon(*point))
			elif self.latlon_units == "dm":
				self.coordinates_display.set_text("(%s, %s)" % pykarta.geometry.dm_lat_lon(*point))
			else:
				raise Exception
		else:
			self.coordinates_display.set_text("")

	def zoom_cb(self, zoom):
		self.zoom_display.set_text("z%.1f" % zoom)

	# Called when the main window is moved or resized
	def on_configure(self, widget, event):
		#print "Window size:", event.width, event.height
		return False

	#==========================================================================
	# Key bindings
	#==========================================================================

	def on_key_press_in_main(self, widget, event):
		keyname = self.build_keyname(event)

		if keyname == "F11":
			widget = self.builder.get_object("menu_view_fullscreen")
			widget.set_active(not widget.get_active())
			return True

		return False

	def on_key_press_in_treeview(self, widget, event):
		keyname = self.build_keyname(event)

		if keyname == 'ctrl-c':
			self.edit_menu.on_copy(widget)
			return True
		if keyname == 'ctrl-x':
			self.edit_menu.on_cut(widget)
			return True
		if keyname == 'ctrl-v':
			self.edit_menu.on_paste(widget)
			return True
		if keyname == "Delete":
			self.edit_menu.on_delete(widget)
			return True

		return False

	def build_keyname(self, event):	
		keys = []
		if event.state & gtk.gdk.CONTROL_MASK:
			keys.append("ctrl")
		if event.state & gtk.gdk.MOD1_MASK:
			keys.append("alt")
		if event.state & gtk.gdk.SHIFT_MASK:
			keys.append("shift")
		keys.append(gtk.gdk.keyval_name(event.keyval))
		keyname = "-".join(keys)
		return keyname

	#=============================================================
	# Menubar support
	#=============================================================

	# Hack for Mac
	# Without a call to this the checkboxes next to checkbox 
	# and radio items don't change.
	def mac_sync_menubar(self):
		if self.macapp:
			self.macapp.sync_menubar()

	#==========================================================================
	# File menu
	#==========================================================================

	def on_file_new(self, widget):
		print "File->New"
		if self.close_ok():
			self.clear()

	def on_file_open(self, widget):
		print "File->Open"
		if not self.close_ok():
			return
		self.clear()
		filename = self.choose_file(
			title="Open",
			action='open',
			filetypes=[
				["GPS Exchange Files", ["*.gpx", "*.gpx.gz"]]
				]
			)
		if not filename:
			return
		self.open_files([filename])

	def on_file_save(self, widget):
		print "File->Save"
		self.save(self.save_filename)	# could be None

	def on_file_save_as(self, widget):
		print "File->Save As"
		self.save(None)

	def on_file_import_gpsr(self, widget):
		print "File->Import from GPSr"

		gpsr_index = self.builder.get_object("gpsr_selector").get_active()
		if gpsr_index == -1:
			self.ui.error("No GPSr selected.")
			return

		# Try to load data. If we get any, zoom to it.
		busy = self.appbusy_factory("Downloading data from GPS receiver...")
		mark = self.data.get_mark()
		if self.satnav.load(gpsr_index, self.data):
			self.map.zoom_to_extent(self.data.get_bbox(mark=mark))

	def on_file_import_file(self, widget):
		print "File->Import from File"
		filename = self.choose_file(
			title="Import",
			action='open',
			filetypes=[
				["GPS Exchange Files", ["*.gpx", "*.gpx.gz"]],
				["LOC Files", ["*.loc"]]
				]
			)
		if not filename:
			return
		self.import_files([filename])

	def on_file_import_tracks(self, widget):
		print "File->Import Preprocessed Tracks"

		# We will look for tracks which cross the bounding box of the current map view.
		map_bbox = self.map.get_bbox()

		# Files output by gpx-track-proprocessor have the bounding box in the file name.
		# track_20080805_44.766400,-68.710580,44.319430,-68.177950.gpx.gz
		filename_pattern = re.compile("track_\d\d\d\d\d\d\d\d_([0-9\.-]+),([0-9\.-]+),([0-9\.-]+),([0-9\.-]+)\.")

		# We use this regexp to make sure that the track actual crosses the map.
		# Note that we are cheating: we can get away with not using an actual
		# XML parser because we are reading only files which gpx-track-processor
		# generated.
		# <trkpt lat="42.096480999999997" lon="-72.724260999999998">
		point_pattern = re.compile('<trkpt lat="([0-9\.-]+)" lon="([0-9\.-]+)">')

		busy = self.appbusy_factory("Importing tracks which cross the map view...")
		for filename in glob.glob(os.path.join(self.processed_tracks_dir, "track_*.gpx.gz")):
			print filename

			# Extract the track's bounding box from its file name.
			m = filename_pattern.match(os.path.basename(filename))
			assert m
			track_bbox = pykarta.geometry.BoundingBox((float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))))

			# Start by testing whether the bounding boxes overlap. If they do,
			# we will open the file and examine the points.
			if map_bbox.overlaps(track_bbox):
				print " bounding boxes overlap"

				# Now open the file and perform a quick-and-dirty check to make
				# sure at least one point is inside the map viewport.
				fh = self.open_gz_r(filename)
				crosses = False
				for line in fh:
					m = point_pattern.search(line)
					if m:
						point = pykarta.geometry.Point(float(m.group(1)), float(m.group(2)))
						if map_bbox.contains_point(point):
							crosses = True
							break

				if crosses:
					print " crosses view"
					if filename in self.loaded_tracks:
						print " was already loaded"
					else:
						print " loading"
						fh.rewind()
						self.data.load_gpx(fh)
						self.loaded_tracks.add(filename)

	def on_file_load_photographs(self, widget):
		print "File->Load Photographs"
		folder = self.choose_file(title=_("Choose Folder"), action='open_folder')
		if not folder:
			return
		busy = self.appbusy_factory(_("Loading photographs from %s...") % folder)
		for dirpath, dirnames, filenames in os.walk(folder):
			for filename in fnmatch.filter(filenames, "*.jpg"):
				full_filename = os.path.join(dirpath, filename)
				self.photos.add_photo(full_filename)

	def on_file_document_properties(self, widget):
		print "File->Document properties"

		# It might be nice if this were stored in the object definitions,
		# but I got too confused when I tried to set that up.
		rules = [
			['name'],
			['desc'],
			['author', 'name'],
			['author', 'email', 'id'],
			['author', 'email', 'domain'],
			['author', 'link', 'text'],
			['author', 'link', 'href'],
			['author', 'link', 'type'],
			['copyright', 'author'],
			['copyright', 'year'],
			['copyright', 'license'],
			['link', 'text'],
			['link', 'href'],
			['link', 'type'],
			['time'],
			['keywords'],
			]

		if self.data.metadata == None:
			self.data.metadata = GpxMetadata()

		# Load the values into the dialog and remember the values in values[].
		values = []
		for rule in rules:
			print "rule:", rule
			value = self.data.metadata.get_item(rule)
			if value == None:
				value = ""
			values.append(value)
			self.builder.get_object("metadata_" + "_".join(rule)).set_text(value)

		# Display the dialog so that the user can change values.
		dialog = self.builder.get_object("MetadataDialog")
		answer = dialog.run()
		dialog.hide()

		# If the user pressed OK (rather than Cancel),
		if answer == 1:
			print "User wants to save changes"
			for rule in rules:
				print "rule:", rule
				value = self.builder.get_object("metadata_" + "_".join(rule)).get_text()
				if value != values.pop(0):		# if value has changed
					print " changed"
					self.data.metadata.set_item(rule, value)

	def on_file_print(self, widget):
		print "File->Print"
		busy = self.appbusy_factory("Printing...")

		cropbox = self.cropbox_layer.get_cropbox()
		if cropbox:
			width, height, margin = cropbox
		else:
			width = self.map.width
			height = self.map.height
			margin = 25
		landscape = width > height

		# Create a new map object for printing with the same layers and viewport as the map widget.
		map_printer = MapPrint(self.map, main_window=self.main_window, landscape=landscape, margin=margin)

		result = map_printer.do_print()
		if result is not None:
			self.ui.error(_("Printing failed: %s") % result)

	def on_file_offline_mode(self, menuitem):
		print "File-->Offline Mode"
		self.map.set_offline(menuitem.get_active())
		self.mac_sync_menubar()

	def on_file_exit(self, widget, data=None):
		print "File->Exit"
		if self.close_ok():
			gtk.main_quit()

	# Window manager close button
	# Not really part of the file menu, but where else can it go?
	def on_wm_close(self, widget, data=None):
		print "WM close"
		if self.close_ok():
			gtk.main_quit()
		return True		# prevents WM from closing

	#==========================================================================
	# Support for File menu
	#==========================================================================

	# Is it OK to close the current document?
	def close_ok(self):
		if self.data.get_changes():
			dialog = self.builder.get_object("SaveCancelDiscardDialog")
			answer = dialog.run()
			dialog.hide()
			if answer == 0:			# User pressed button "Close without Saving"
				return True
			elif answer == 2:		# User pressed "Save"
				if not self.save(self.save_filename):
					return False	# save failed
			else:					# User pressed "Cancel" or closed the dialog box
				return False
		return True

	# Clear out the data leaving a blank nameless document.
	def clear(self):
		self.data.clear()	
		self.set_save_filename(None)
		self.first_picker.reset()

	# Clear the document and load the files named. Zoom and pan to the best show the objects.
	def open_files(self, gpx_files):
		try:
			self.clear()

			# Add each file to the data store
			for filename in gpx_files:
				busy = self.appbusy_factory(_("Loading %s...") % filename)
				self.data.load_gpx(self.open_gz_r(filename))
	
			# If we loaded from only one file, that is the file to which we expect to save.
			if len(gpx_files) == 1:
				self.set_save_filename(gpx_files[0])

			# Loading the data will have set the changed-document indicator. Clear it.
			self.data.clear_changes()

			# Bring the loaded objects into view.
			self.map.zoom_to_extent(self.data.get_bbox())
		except Exception, e:
			self.ui.exception(_("Loading file"), e)

	# Load more data from the files named. Zoom and pan to best show the new objects.
	def import_files(self, gpx_files):
		mark = self.data.get_mark()
		for filename in gpx_files:
			busy = self.appbusy_factory(_("Importing %s...") % filename)
			if os.path.splitext(filename)[1] == ".loc":
				import gpx_import_loc
				gpx_import_loc.load_loc(filename, self.data)
			else:
				self.data.load_gpx(self.open_gz_r(filename))
		self.map.zoom_to_extent(self.data.get_bbox(mark=mark))

	# Open a file (possibly in Gzip format) for read.
	def open_gz_r(self, filename):
		if os.path.splitext(filename)[1] == ".gz":
			import gzip
			return gzip.open(filename, "r")
		else:
			return open(filename, "r")

	# This function does the actual work of saving the current document.
	# * If filename is None, ask the user to choose one.
	# * Make filename the new name of the loaded file.
	def save(self, filename):
		if not filename:
			filename = self.choose_file(
				title="Save As",
				action='save',
				filetypes=[
					["GPS Exchange Files", ["*.gpx"]]
					]
				)
			if not filename:
				return False

			if os.path.splitext(filename)[1] != ".gpx":
				filename = "%s.gpx" % filename

			if os.path.exists(filename):
				if not self.ui.yesno_question(_("File exists. Overwrite?")):
					return False

		tmpfile = "%s.tmp" % filename
		bakfile = "%s.bak" % filename

		busy = self.appbusy_factory(_("Saving to %s...") % filename)
		f = open(tmpfile, "w")
		writer = GpxWriter(f)
		self.data.write(writer)
		writer = None
		f.close()

		if os.path.exists(filename):
			if os.path.exists(bakfile):
				os.unlink(bakfile)
			os.rename(filename, bakfile)
		os.rename(tmpfile, filename)

		self.data.clear_changes()
		self.set_save_filename(filename)
		return True

	# This not only sets self.save_filename, it also updates the title of the main window.
	def set_save_filename(self, filename):
		if filename:
			dirname, basename = os.path.split(filename)
			desc = _("%s (%s)") % (basename, dirname)
		else:
			desc = _("Unsaved GPX file")
		self.main_window.set_title(_("%s - GPX Trip Planner") % desc)
		self.save_filename = filename

	# Invoke the Gtk file chooser.
	# See: http://www.pygtk.org/pygtk2tutorial/sec-FileChoosers.html
	def choose_file(self, title="Choose File", action='open', filetypes=[]):
 		if action == 'open':
			button=gtk.STOCK_OPEN
			action=gtk.FILE_CHOOSER_ACTION_OPEN
		elif action == 'save':
			button=gtk.STOCK_SAVE
			action = gtk.FILE_CHOOSER_ACTION_SAVE
 		elif action == 'open_folder':
			button=gtk.STOCK_OPEN
			action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER
		else:
			raise NotImplementedError

		chooser = gtk.FileChooserDialog(
			title=title,
			action=action,
			buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,button,gtk.RESPONSE_OK)
			)

		# Some versions of Gtk+ like to display a (likely empty) list 
		# of recently opened files. We consider this unhelpful in the
		# context of this application and so explicitly direct it to
		# show the current directory.
		chooser.set_current_folder(os.getcwd())

		if len(filetypes) >= 1:
			for filetype in filetypes:
				filter = gtk.FileFilter()
				filter.set_name(filetype[0])
				for pattern in filetype[1]:
					filter.add_pattern(pattern)
				chooser.add_filter(filter)

		response = chooser.run()
		filename = chooser.get_filename()
		chooser.destroy()
		if response == gtk.RESPONSE_OK:
			return filename
		else:
			return None

	# Put up a watch cursor.
	def appbusy_factory(self, message):
		return AppBusy(self.main_window, self.ui.statusbar, message)

	#==========================================================================
	# Edit Menu
	#==========================================================================

	def edit_paste_search_cb(self, pasted_text):
		self.sidebar.set_current_page(3)	# search
		self.builder.get_object("search_terms").set_text(pasted_text)

	#==========================================================================
	# View Menu
	#==========================================================================

	def on_view_fullscreen(self, menuitem):
		print "View-->Fullscreen"
		if menuitem.get_active():		# checked
			self.main_window.fullscreen()
		else:							# unchecked
			self.main_window.unfullscreen()
		self.mac_sync_menubar()

	def on_view_sidebar(self, menuitem):
		print "View-->Sidebar"
		if menuitem.get_active():		# checked
			self.sidebar.show()
		else:							# unchecked
			self.sidebar.hide()
		self.mac_sync_menubar()

	def on_view_maps(self, menuitem):
		if menuitem.get_active():
			choice = int(gtk.Buildable.get_name(menuitem).split(":")[1])
			print "View->Map Choices:", choice
			menus = self.builder.get_object("MapMenu").get_children()
			sep = None
			for layer in gpx_reference_layers.layers:
				menu = menus.pop(0)
				if layer:	# not separator
					if layer.importance <= choice:
						if sep:
							sep.show()
						menu.show()
					else:
						menu.hide()
				else:
					menu.hide()
					sep = menu

	# Add menu options for the map layers
	def init_view_map_tiles(self):
		i = 0	# after first separator
		menu = self.builder.get_object("MapMenu")

		layers = list(gpx_reference_layers.layers)[:]
		mbtiles_files = glob.glob("*.mbtiles")
		if len(mbtiles_files) > 0:
			layers.append(None)		# separator
			for mbtiles_file in mbtiles_files:
				layers.append(gpx_reference_layers.GpxTileLayer(1, mbtiles_file, mbtiles_file))

		group = None
		sep = None
		for layer in layers:
			if layer:
				if layer.overlay:
					menuitem = gtk.CheckMenuItem(label=layer.display_name)
					menuitem.connect("activate", self.on_overlay_layer_toggle, layer)
				else:
					menuitem = gtk.RadioMenuItem(group=group, label=layer.display_name)
					menuitem.connect("activate", self.on_base_layer_change, layer)
					if group is None:
						group = menuitem
				if layer.tooltip:
					menuitem.set_tooltip_text(layer.tooltip)
				if layer.default:
					menuitem.set_active(True)
			else:	# separator
				menuitem = gtk.SeparatorMenuItem()
				sep = menuitem
			menu.insert(menuitem, i)
			if layer is not None and layer.importance <= 1:
				if sep:
					sep.show()
				menuitem.show()
			i += 1

	# Called whenever the base map layer is changed
	def on_base_layer_change(self, button, layer):
		if button.get_active():		# If button pressed in,
			print "Changing tile source to %s" % str(layer.tileset_names)
			self.map.set_tile_source(layer.tileset_names)
			self.builder.get_object("MapMenuButton").set_label(layer.display_name)
			#self.mac_sync_menubar()

	# Called whenever an overlay layer is turned on or off
	def on_overlay_layer_toggle(self, button, layer):
		print button.get_active(), layer.tileset_names
		if button.get_active():		# if pressed in,
			for tileset_name in layer.tileset_names:
				if tileset_name == "mapquest-traffic":
					layer_obj = pykarta.maps.layers.mapquest.MapTrafficLayer()
				else:
					tileset = pykarta.maps.tilesets.tilesets[tileset_name]
					layer_obj = pykarta.maps.layers.MapTileLayerHTTP(tileset)
				self.map.add_layer(tileset_name, layer_obj, overlay=True)
		else:
			for tileset_name in layer.tileset_names:
				self.map.remove_layer(tileset_name)

	def on_view_crop_lines(self, button):
		if button.get_active():
			button_name = gtk.Buildable.get_name(button)
			print "Map size:", button_name
			width, height, margin = map(int, button_name.split(':')[1:])
			if width:
				self.cropbox_layer.set_cropbox((width, height, margin))
			else:
				self.cropbox_layer.set_cropbox(None)
			self.mac_sync_menubar()

	def on_view_units(self, button):
		if button.get_active():
			button_name = gtk.Buildable.get_name(button)
			print "Lat/Lon Format:", button_name
			self.latlon_units = button_name.split(':')[1]
			self.mac_sync_menubar()

	#==========================================================================
	# Bookmarks Menu
	#==========================================================================
	def init_bookmarks(self):
		print "Loading bookmarks..."
		self.bookmarks_menu = self.builder.get_object("MenuBookmarksMenu")
		self.bookmarks = []
		if os.path.exists(self.bookmarks_filename):
			bookmarks_file = csv.reader(codecs.open(self.bookmarks_filename, "rb", "utf-8"))
			for name, lat, lon, zoom in bookmarks_file:
				# FIXME: causes Python to abort if there are unicode bookmarks in non-unicode locale
				#print " ", name
				self.add_bookmark_to_menu((name, float(lat), float(lon), float(zoom)))

	def add_bookmark_to_menu(self, bookmark):
		i = len(self.bookmarks) 
		self.bookmarks.append(bookmark)
		menuitem = gtk.MenuItem(bookmark[0])
		menuitem.connect("activate", self.on_bookmark, i)
		self.bookmarks_menu.insert(menuitem, i+2)	# after separator
		menuitem.show()

	def on_bookmarks_add(self, button):
		print "Bookmarks->Add"
		dialog = self.builder.get_object("CreateBookmarkDialog")
		entry = self.builder.get_object("CreateBookmarkName")
		entry.set_text("")
		answer = dialog.run()
		dialog.hide()
		if answer != 1:		# 1 is OK
			print "User canceled bookmark creation"
			return
		name = entry.get_text().strip()
		if name == "":
			print "User did not provide a bookmark name"
			return

		lat, lon, zoom = self.map.get_center_and_zoom()
		bookmarks_file = csv.writer(codecs.open(self.bookmarks_filename, "ab", "utf-8"))
		bookmarks_file.writerow((name, str(lat), str(lon), str(zoom)))

		self.add_bookmark_to_menu((name, lat, lon, zoom))

	def on_bookmark(self, button, i):
		bookmark = self.bookmarks[i]
		print "Bookmark:", bookmark
		name, lat, lon, zoom = bookmark
		self.map.set_center_and_zoom(lat, lon, zoom)

	#==========================================================================
	# Tools Menu
	#==========================================================================

	def on_tools_precache_tiles(self, widget):
		print "Tools->Precache Tiles"
		self.map.precache_tiles(main_window=self.main_window, max_zoom=15)

	def on_tools_reload_tiles(self, widget):
		print "Tools->Reload Tiles"
		self.map.reload_tiles()

	def on_tools_assoc(self, widget):
		print "Tools->Associate GPX and LOC files"
		if self.ui.yesno_question(_("Do you want to associate GPX and LOC files with this program?")):
			import gpx_assoc
			gpx_assoc.set_associations(self.ui)

	def on_tools_update(self, widget):
		print "Tools->Update Program"
		busy = self.appbusy_factory("Updating program...")
		import urllib2
		try:
			self.module_updaters = []
			new_updaters = []
			self.package_updates = utils_updater.download_simple_update(self.ui.show_status)
		except urllib2.HTTPError as e:
			self.ui.error(
				_("The attempt to download a newer version of this application " \
				  "has failed. Please try again later.\n\n" \
				  "Error code: {error_code}").format(error_code=e.code)
				)
		except Exception as e:
			self.ui.exception(_("Update of Application"), e)

	#==========================================================================
	# Help Menu
	#==========================================================================

	def on_help_about(self, widget):
		app_info = utils_updater.load_package_info(os.path.join(sys.path[0], "Code_info.xml"))
		dialog = self.builder.get_object("AboutDialog")
		dialog.set_version(_("version {version}").format(version=app_info['display_version']))
		answer = dialog.run()
		dialog.hide()

	#==========================================================================
	# Search pane
	#==========================================================================

	def on_search_go(self, widget):
		search_terms = self.builder.get_object("search_terms").get_text()
		if self.builder.get_object("search_scope_anywhere").get_active():
			scope = "scope_anywhere"
		elif self.builder.get_object("search_scope_usa").get_active():
			scope = "scope_usa"
		elif self.builder.get_object("search_scope_within").get_active():
			scope = "scope_within"

		self.search_results.clear()
		busy = self.appbusy_factory("Searching...")
		m = search_nominatim(search_terms, scope=scope, bbox=self.map.get_bbox())
		if len(m) > 0:
			bbox = pykarta.geometry.BoundingBox()
			for point in m:
				self.search_results.append(point)
				bbox.add_point(pykarta.geometry.Point(point.lat, point.lon))
			if len(m) > 1:
				self.map.zoom_to_extent(bbox)
			else:
				self.search_results.select((0,), "gui")

	def on_search_clear(self, widget):
		self.search_results.clear()

# end of file
