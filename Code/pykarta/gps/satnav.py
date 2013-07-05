# pykarta/gps/satnavs.py
# Last modified: 7 March 2013

# See https://code.google.com/p/pybluez/
import bluetooth

# See http://www.tomtom.com/lib/doc/ttnavsdk3_manual.pdf
class TomtomBT(object):
	def __init__(self, address):
		print "BtTomTom(%s)" % str(address)
		self.sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
		self.sock.connect(address)
		result = self.sock.recv(1024)
		if result != "HELLO\n":
			raise Exception("No HELLO: %s" % result)

	def api_call(self, *command):
		print "api_call(%s)" % str(command)
		self.sock.sendall("API %s|\n" % ("|".join(map(str, command))))

		print "Waiting for response..."
		result_text = ""
		while True:
			i = self.sock.recv(1024)
			if i == "":
				break
			result_text += i
			if result_text[-1] == "\n":
				break 

		print "Response:", result_text	
		result = result_text.split("|")[:-1]
		if result[0] != '0':
			raise Exception("API call failed: %s" % result_text)
		return result

	def GetApplicationVersion(self):
		result = self.api_call("GetApplicationVersionV01")
		return (float(result[1]), int(result[2]))

	def FlashMessage(self, message, duration=2000):
		self.api_call("FlashMessage", message, duration)

	def GetFavorite(self, index):
		result = self.api_call("GetFavoriteV01", index)
		return result

	def SwitchToNavigatorView(self):
		self.api_call("SwitchToNavigatorView")

	def GetCurrentPosition(self):
		code, mystery, lon, lat, heading, speed = self.api_call("GetCurrentPositionV01")
		return (float(lat) / 100000.0, float(lon) / 100000.0, int(heading), int(speed))

	def NavigateToCoordinates(self, lat, lon, name):
		self.api_call("NavigateToCoordinatesV01", int(lon * 100000 + 0.5), int(lat * 100000 + 0.5), name) 

	def ShowCoordinatesOnMap(self, lat, lon):
		self.api_call("ShowCoordinatesOnMapV01", int(lon * 100000 + 0.5), int(lat * 100000 + 0.5)) 

	def ShowRectangleOnMap(self, min_lon, min_lat, max_lon, max_lat):
		self.api_call("ShowRectangleOnMap",
			int(min_lon * 100000 + 0.5),
			int(min_lat * 100000 + 0.5),
			int(max_lon * 100000 + 0.5),
			int(max_lat * 100000 + 0.5)
			)

if __name__ == "__main__":
	tomtom = TomtomBT(("00:13:6C:1E:CE:AB", 2))
	#print tomtom.GetApplicationVersion()
	#tomtom.FlashMessage("Test")
	#print tomtom.GetFavorite(0)
	#print tomtom.GetCurrentPosition()
	tomtom.ShowRectangleOnMap(-72.72427, 42.09626, -72.68712, 41.74645)
	#tomtom.NavigateToCoordinates(41.74645, -72.68712, "Test Destination")
	#tomtom.ShowCoordinatesOnMap(41.74645, -72.68712)
	
