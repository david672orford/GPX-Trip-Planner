# encoding=utf-8
# Copyright 2013--2025, Trinity College

class GpxTileLayer:
	def __init__(self, importance, display_name, tileset_names, default=False, tooltip=None, overlay=False):
		self.importance = importance
		self.display_name = display_name
		if isinstance(tileset_names, str):
			self.tileset_names = [tileset_names]
		else:
			self.tileset_names = tileset_names
		self.default = default
		self.tooltip = tooltip
		self.overlay = overlay

layers = (
	GpxTileLayer(1, _("OSM Standard"), "osm-default", default=True),
	GpxTileLayer(1, _("OSM Standard HD"), "osm-default-hd"),
	GpxTileLayer(1, _("OSM Vector"), "osm-vector"),
	GpxTileLayer(1, _("OSM OpenCycleMap"), "osm-thunderforest-cycle"),
	GpxTileLayer(1, _("OSM Public Transport"), "osm-thunderforest-transport"),
	GpxTileLayer(2, _("OSM Public Transport Dark"), "osm-thunderforest-transport-dark"),
	GpxTileLayer(1, _("OSM Humanitarian"), "osm-humanitarian"),
	GpxTileLayer(2, _("OSM Mapbox Streets"), "osm-mapbox-streets"),
	GpxTileLayer(2, _("OSM Carto Light"), "osm-carto-light"),
	GpxTileLayer(2, _("OSM Carto Dark"), "osm-carto-dark"),
	GpxTileLayer(2, _("OSM Thunderforest Landscape"), "osm-thunderforest-landscape"),
	GpxTileLayer(2, _("OSM Thunderforest Outdoors"), "osm-thunderforest-outdoors"),
	GpxTileLayer(2, _("OSM Thunderforest Pioneer"), "osm-thunderforest-pioneer"),
	GpxTileLayer(2, _("OSM Thunderforest Mobile Atlas"), "osm-thunderforest-mobile-atlas"),
	GpxTileLayer(2, _("OSM Thunderforest Neighbourhood"), "osm-thunderforest-neighbourhood"),
	None,
	GpxTileLayer(1, _("Blank White"), []),
	GpxTileLayer(1, _("Overlay Parcel Borders"), "parcels-pykarta", overlay=True),
	GpxTileLayer(1, _("Overlay Tile Borders"), "tile-debug", overlay=True),
	GpxTileLayer(1, _("OSM Waymarkedtrails Hiking"), "osm-waymarkedtrails-hiking", overlay=True),
	GpxTileLayer(1, _("OSM Waymarkedtrails Cycling"), "osm-waymarkedtrails-cycling", overlay=True),
	GpxTileLayer(2, _("OSM Vector Landuse"), "osm-vector-landuse", overlay=True),
	GpxTileLayer(2, _("OSM Vector Roads"), "osm-vector-roads", overlay=True),
	GpxTileLayer(2, _("OSM Vector Waterways"), "osm-vector-waterways", overlay=True),
	GpxTileLayer(2, _("OSM Vector Waterbodies"), "osm-vector-water", overlay=True),
	GpxTileLayer(2, _("OSM Vector Buildings"), "osm-vector-buildings", overlay=True),
	GpxTileLayer(2, _("OSM Vector Admin Borders"), "osm-vector-admin-borders", overlay=True),
	GpxTileLayer(2, _("OSM Vector Road Labels"), "osm-vector-road-labels", overlay=True),
	GpxTileLayer(2, _("OSM Vector Place Labels"), "osm-vector-places", overlay=True),
	GpxTileLayer(2, _("OSM Vector POI Labels"), "osm-vector-pois", overlay=True),
	None,
	#GpxTileLayer(1, _("OSM Stamen Toner"), ("osm-stamen-toner")),
	#GpxTileLayer(1, _("OSM Stamen Toner Lite"), ("osm-stamen-toner-lite")),
	#GpxTileLayer(2, _("OSM Stamen Toner Background"), ("osm-stamen-toner-background", "screen-0.7")),
	#GpxTileLayer(2, _("OSM Stamen Toner Lines"), "osm-stamen-toner-lines", overlay=True),
	#GpxTileLayer(2, _("OSM Stamen Toner Labels"), "osm-stamen-toner-labels", overlay=True),
	#None,
	#GpxTileLayer(1, _("OSM Stamen Terrain"), "osm-stamen-terrain"),
	#GpxTileLayer(2, _("OSM Stamen Terrain Background"), ("osm-stamen-terrain-background", "screen-0.7")),
	#GpxTileLayer(2, _("OSM Stamen Terrain Lines"), "osm-stamen-terrain-lines", overlay=True),
	#GpxTileLayer(2, _("OSM Stamen Terrain Labels"), "osm-stamen-terrain-labels", overlay=True),
	#GpxTileLayer(1, _("OSM TopOSM (USA Only)"), ("osm-toposm-color-relief", "osm-toposm-contours", "osm-toposm-features")),
	GpxTileLayer(1, _("OSM OpenTopoMap"), "osm-opentopomap"),
	GpxTileLayer(1, _("USGS Topos (ArcGIS)"), "arcgis-usa-topo"),
	#GpxTileLayer(3, _("MassGIS USGS Topos"), "massgis-usgs-topos"),	# broken
	None,
	GpxTileLayer(2, _("Blue Marble"), "modestmaps-bluemarble"),
	#GpxTileLayer(2, _("Bing Aerial"), "bing-aerial"),
	#GpxTileLayer(2, _("Bing Aerial with Labels"), "bing-aerial-with-labels"),
	#GpxTileLayer(1, _("Bing Aerial with Roads and Labels"), ("bing-aerial", "osm-openmapsurfer-hybrid")),
	GpxTileLayer(2, _("ArcGIS World Imagery"), "arcgis-world-imagery"),
	GpxTileLayer(1, _("ArcGIS World Imagery Hybrid"), ("arcgis-world-imagery", "arcgis-world-reference-overlay")),
	None,
	#GpxTileLayer(2, _("Bing Road"), "bing-road"),
	GpxTileLayer(2, _("ArcGIS DeLorme World Basemap"), "arcgis-delorme-world-basemap"),
	GpxTileLayer(2, _("ArcGIS National Geographic World Map"), "arcgis-natgeo-world"),
	None,
	GpxTileLayer(3, _("MassGIS L3 Parcels"), "massgis-l3parcels", overlay=True),
	GpxTileLayer(3, _("MassGIS Orthos 199X"), "massgis-orthos-199X"),
	GpxTileLayer(3, _("MassGIS Orthos 2005"), "massgis-orthos-2005"),
	GpxTileLayer(3, _("MassGIS Orthos 2009"), "massgis-orthos-2009"),
	GpxTileLayer(3, _("MassGIS Orthos 2014"), "massgis-orthos-2014"),
	)
