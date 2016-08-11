# encoding=utf-8
# gpx_reference_layers.py
# Copyright 2013, 2014, Trinity College
# Last modified: 1 October 2014

class GpxTileLayer(object):
	def __init__(self, importance, display_name, tileset_names, default=False, tooltip=None, overlay=False):
		self.importance = importance
		self.display_name = display_name
		if isinstance(tileset_names, basestring):
			self.tileset_names = [tileset_names]
		else:
			self.tileset_names = tileset_names
		self.default = default
		self.tooltip = tooltip
		self.overlay = overlay

layers = (
	GpxTileLayer(1, _("Blank White"), []),
	GpxTileLayer(1, _("OSM Experimental Vector"), "osm-vector", default=True),
	GpxTileLayer(1, _("OSM Openmapsurfer"), "openmapsurfer-roads", default=False),
	None,
	# Layers on www.openstreetmap.org slippy map
	GpxTileLayer(1, _("OSM Standard"), "osm-default"),
	GpxTileLayer(2, _("OSM Standard without labels"), "toolserver-osm-no-labels"),
	GpxTileLayer(1, _("OSM Cycle Map"), "osm-cycle"),
	GpxTileLayer(1, _("OSM Public Transport"), "osm-transport"),
	GpxTileLayer(1, _("OSM Humanitarian"), "osm-humanitarian"),
	GpxTileLayer(1, _("OSM HikeBikeMap"), "toolserver-hikebike"),
	None,
	GpxTileLayer(1, _("OSM Stamen Toner Background"), ("stamen-toner-background", "screen-0.7")),
	GpxTileLayer(1, _("OSM Stamen Toner Labels"), "stamen-toner-labels", overlay=True),
	GpxTileLayer(1, _("OSM Stamen Terrain"), "stamen-terrain"),
	GpxTileLayer(1, _("OSM TopOSM"), ("toposm-color-relief", "toposm-contours", "toposm-features")),
	GpxTileLayer(1, _("OSM Mapbox Streets"), "mapbox-streets"),
	None,
	GpxTileLayer(1, _("Overlay Hillshading"), "toolserver-hillshading", overlay=True),
	GpxTileLayer(1, _("Overlay Parcel Borders"), "tc-parcels", overlay=True),
	GpxTileLayer(1, _("Overlay Tile Borders"), "tile-debug", overlay=True),
	None,
	GpxTileLayer(1, _("Bing Aerial/OSM Hybrid"), ("bing-aerial", "geoiq-acetate")),
	GpxTileLayer(1, _("Blue Marble"), "modestmaps-bluemarble"),
	None,
	GpxTileLayer(2, _("ArcGIS World Imagery"), "arcgis-world-imagery"),
	GpxTileLayer(2, _("ArcGIS World Imagery Hybrid"), ("arcgis-world-imagery", "arcgis-world-reference-overlay")),
	GpxTileLayer(2, _("ArcGIS USGS Topos"), "arcgis-usa-topo"),
	GpxTileLayer(2, _("ArcGIS DeLorme World Basemap"), "arcgis-delorme-world-basemap"),
	GpxTileLayer(2, _("ArcGIS National Geographic World Map"), "arcgis-natgeo-world"),
	None,
	GpxTileLayer(2, _("Bing Road"), "bing-road"),
	GpxTileLayer(2, _("Bing Aerial"), "bing-aerial"),
	GpxTileLayer(2, _("Bing Aerial with Labels"), "bing-aerial-with-labels"),
	None,
	GpxTileLayer(3, _("MassGIS L3 Parcels"), "massgis-l3parcels", overlay=True),
	GpxTileLayer(1, _("MassGIS Orthos 199X"), "massgis-orthos-199X"),
	GpxTileLayer(1, _("MassGIS Orthos 2005"), "massgis-orthos-2005"),
	GpxTileLayer(1, _("MassGIS Orthos 2009"), "massgis-orthos-2009"),
	GpxTileLayer(1, _("MassGIS Orthos 2014"), "massgis-orthos-2014"),
	GpxTileLayer(3, _("MassGIS USGS Topos"), "massgis-usgs-topos"),
	)

