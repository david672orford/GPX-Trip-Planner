# encoding=utf-8
# gpx_reference_layers.py
# Copyright 2013, 2014, Trinity College
# Last modified: 19 July 2014

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
	GpxTileLayer(1, _("Blank White"), ()),
	GpxTileLayer(1, _("OSM Standard"), "osm-default"),
	GpxTileLayer(2, _("OSM Cycle"), "osm-cycle"),
	GpxTileLayer(3, _("OSM Public Transport"), "osm-transport"),
	GpxTileLayer(3, _("OSM Humanitarian"), "osm-humanitarian"),
	GpxTileLayer(2, _("OSM Openbusmap"), "opnvkarte"),
	GpxTileLayer(1, _("OSM Mapquest"), "mapquest-osm", default=True),
	GpxTileLayer(2, _("OSM Openstreetbrowser"), "openstreetbrowser"),
	GpxTileLayer(1, _("OSM TopOSM"), ("toposm-color-relief", "toposm-contours", "toposm-features")),
	GpxTileLayer(3, _("OSM B&W"), "toolserver-bw-mapnik"),
	GpxTileLayer(3, _("OSM No Labels"), "toolserver-osm-no-labels"),
	GpxTileLayer(2, _("OSM Russian Labels"), ("toolserver-osm-no-labels", "toolserver-osm-labels-ru")),
	GpxTileLayer(2, _("OSM Stamen Toner"), "stamen-toner"),
	GpxTileLayer(1, _("OSM Stamen Toner Lite"), ("stamen-toner-lite", "screen-0.4")),
	GpxTileLayer(1, _("OSM Stamen Toner Background"), ("stamen-toner-background", "screen-0.7")),
	GpxTileLayer(1, _("OSM Stamen Terrain"), "stamen-terrain"),
	GpxTileLayer(2, _("Mapbox Streets"), "mapbox-streets"),
	GpxTileLayer(1, _("Overlay Hillshading"), "toolserver-shadows", overlay=True),
	None,
	GpxTileLayer(2, _("Openaerial"), "mapquest-openaerial"),
	GpxTileLayer(2, _("Openaerial/OSM Hybrid"), ("mapquest-openaerial", "geoiq-acetate")),
	GpxTileLayer(2, _("Mapbox Satellite"), "mapbox-josm"),
	GpxTileLayer(2, _("Mapbox Satellite/OSM Hybrid"), ("mapbox-josm", "geoiq-acetate")),
	GpxTileLayer(1, _("Bing Aerial"), "bing-aerial"),
	GpxTileLayer(1, _("Bing Aerial/OSM Hybrid"), ("bing-aerial", "geoiq-acetate")),
	GpxTileLayer(2, _("ArcGIS World Imagery"), "arcgis-world-imagery"),
	GpxTileLayer(2, _("ArcGIS World Imagery Hybrid"), ("arcgis-world-imagery", "arcgis-world-reference-overlay")),
	None,
	GpxTileLayer(1, _("USGS Topos (thru ArcGIS)"), "arcgis-usa-topo"),
	None,
	GpxTileLayer(1, _("DeLorme World Basemap"), "arcgis-delorme-world-basemap"),
	GpxTileLayer(1, _("National Geographic World Map"), "arcgis-natgeo-world"),
	None,
	GpxTileLayer(2, _("Bing Road"), "bing-road"),
	GpxTileLayer(3, _("Bing Aerial"), "bing-aerial"),
	GpxTileLayer(2, _("Bing Aerial with Labels"), "bing-aerial-with-labels"),
	None,
	GpxTileLayer(2, _("Mapquest Map"), "mapquest-map"),
	GpxTileLayer(3, _("Mapquest Satellite"), "mapquest-satellite"),
	GpxTileLayer(2, _("Mapquest Hybrid"), ("mapquest-satellite", "mapquest-hybrid")),
	GpxTileLayer(3, _("Mapquest Traffic"), "mapquest-traffic", overlay=True),
	None,
	GpxTileLayer(3, _("MassGIS Base Map"), "massgis-base"),
	GpxTileLayer(3, _("MassGIS USGS Topos"), "massgis-usgs-topos"),
	GpxTileLayer(3, _("MassGIS Orthos 199X"), "massgis-orthos-199X"),
	GpxTileLayer(3, _("MassGIS Orthos 2005"), "massgis-orthos-2005"),
	GpxTileLayer(3, _("MassGIS Orthos 2009"), "massgis-orthos-2009"),
	GpxTileLayer(3, _("MassGIS Orthos 2009 TC"), "massgis-orthos-2009_tc"),
	GpxTileLayer(3, _("MassGIS Labels"), "massgis-labels", overlay=True),
	GpxTileLayer(3, _("MassGIS L3 Parcels"), "massgis-l3parcels", overlay=True),
	GpxTileLayer(3, _("MassGIS Structures"), "massgis-structures", overlay=True),
	)

