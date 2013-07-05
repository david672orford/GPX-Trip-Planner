# Common elements of many of this layers in this program

from pykarta.maps.layers import MapLayer

class GpxVectorLayer(MapLayer):
	def __init__(self):
		MapLayer.__init__(self)
		self.tool = None
		self.layer_objs = []
		self.visible_objs = []
		self.selected_path = None

	# User has selected indicated tool on the toolbar
	# or None if this layer has lost editing focus.
	def set_tool(self, tool):
		self.tool = tool
		self.selected_path = None
		self.layer_objs.select(None, "map_layer")
		self.containing_map.queue_draw()
		return ""

