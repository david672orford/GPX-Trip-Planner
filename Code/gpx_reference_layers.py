# encoding=utf-8
# gpx_reference_layers.py
# Copyright 2013, 2014, Trinity College
# Last modified: 28 March 2014

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
	GpxTileLayer(1, _("OSM Stamen Toner"), "stamen-toner"),
	GpxTileLayer(2, _("OSM Stamen Toner Hybrid"), "stamen-toner-hybrid"),
	GpxTileLayer(2, _("OSM Stamen Toner Lite"), "stamen-toner-lite"),
	GpxTileLayer(3, _("OSM Stamen Toner Background"), "stamen-toner-background"),
	GpxTileLayer(1, _("OSM Stamen Terrain"), "stamen-terrain"),
	GpxTileLayer(3, _("OSM Stamen Watercolor"), "stamen-watercolor"),
	GpxTileLayer(2, _("Mapbox Streets"), "mapbox-streets"),
	GpxTileLayer(1, _("Overlay Hillshading"), "toolserver-shadows", overlay=True),
	GpxTileLayer(3, _("Overlay TIGER 2012 Lines"), "osm-tiger-2012", overlay=True),
	None,
	GpxTileLayer(2, _("Openaerial"), "mapquest-openaerial"),
	GpxTileLayer(2, _("Openaerial/OSM Hybrid"), ("mapquest-openaerial", "geoiq-acetate")),
	GpxTileLayer(2, _("Mapbox Satellite"), "mapbox-josm"),
	GpxTileLayer(2, _("Mapbox Satellite/OSM Hybrid"), ("mapbox-josm", "geoiq-acetate")),
	GpxTileLayer(1, _("Bing Aerial"), "bing-aerial"),
	GpxTileLayer(1, _("Bing Aerial/OSM Hybrid"), ("bing-aerial", "geoiq-acetate")),
	GpxTileLayer(2, _("USGS NAIP"), "osm-usgs_naip"),
	GpxTileLayer(2, _("USGS NAIP/OSM Hybrid"), ("osm-usgs_naip", "geoiq-acetate")),
	GpxTileLayer(2, _("ArcGIS World Imagery"), "arcgis-world-imagery"),
	GpxTileLayer(2, _("ArcGIS World Imagery Hybrid"), ("arcgis-world-imagery", "arcgis-world-reference-overlay")),
	None,
	GpxTileLayer(1, _("USGS Topos (thru ArcGIS)"), "arcgis-usa-topo"),
	#GpxTileLayer(2, _("USGS Topos (thru Openstreetmap.us)"), "osm-usgs_scanned_topos"),
	GpxTileLayer(2, _("USGS Topos (thru Mytopo.com)"), "mytopo"),
	None,
	GpxTileLayer(1, _("DeLorme World Basemap"), "arcgis-delorme-world-basemap"),
	GpxTileLayer(1, _("National Geographic World Map"), "arcgis-natgeo-world"),
	#None,
	#GpxTileLayer(2, _("Google Maps"), "google"),
	#GpxTileLayer(3, _("Google Maps Satellite"), "google-satellite"),
	#GpxTileLayer(2, _("Google Maps Hybrid"), ("google-satellite", "google-hybrid")),
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
	GpxTileLayer(3, _("Nokia OVI Normal"), "nokia-normal"),
	GpxTileLayer(3, _("Nokia OVI Normal Grey"), "nokia-normal-grey"),
	GpxTileLayer(3, _("Nokia OVI Normal Transit"), "nokia-normal-transit"),
	GpxTileLayer(3, _("Nokia OVI Terrain"), "nokia-terrain"),
	GpxTileLayer(3, _("Nokia OVI Satellite"), "nokia-satellite"),
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
	#None,
	#GpxTileLayer(3, _("Westfield Orthos 1940"), 'westfieldgis-orthos-1940'),
	#GpxTileLayer(3, _("Westfield Orthos 1969"), 'westfieldgis-orthos-1969'),
	#GpxTileLayer(3, _("Westfield Parcels"), 'westfieldgis-parcels', overlay=True),
	)

