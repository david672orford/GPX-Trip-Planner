# gpx_import_url.py
# Parsing of online map URLs
# Copyright 2013--2023 Trinity College
# Last modified: 26 March 2023

import re
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen
from gpx_data_gpx import GpxWaypoint

def load_url(url, datastore, ui):
	print("load_url():", url)
	url_obj = urlparse(url)

	# Google short format
	# http://m.google.com/u/m/zpHLyb
	if url_obj.scheme.startswith('http') and url_obj.netloc == 'm.google.com':
		url_obj = urlparse(expand_short_url(url))
	
	# Google long format
	# http://maps.google.com/?source=friendlink&q=41.361092,-73.631644(Southeast,+NY)
	# http://maps.google.com/maps?q=300+summit+street&hl=en&sll=41.763711,-72.685093&sspn=0.192831,0.251312&hnear=300+Summit+St,+Hartford,+Connecticut+06106&t=m&z=16
	# http://maps.google.com/maps?q=palisades+interstate+park&hl=en&ll=40.853326,-73.962622&spn=0.025579,0.03459&sll=41.763711,-72.685093&sspn=0.201794,0.276718&hq=palisades+interstate+park&t=m&z=15&iwloc=A
	# https://maps.google.com/maps?q=61+Steiger+Drive,+Westfield,+MA&hl=en&oq=61+steiger+drive&hnear=61+Steiger+Dr,+Westfield,+Massachusetts+01085&t=m&z=16&iwloc=A
	if url_obj.scheme.startswith('http') and url_obj.netloc == 'maps.google.com':
		query = parse_qs(url_obj.query)
		print("query:", query)
		for field in ['ll', 'sll']:		# locate or search from location?
			if field in query:
				print("%s: %s", (field, query[field][0]))
				m = re.search("^([0-9\.-]+),([0-9\.-]+)", query[field][0])
				if m:
					point = GpxWaypoint(float(m.group(1)), float(m.group(2)))
					if 'q' in query:
						point.name = query['q'][0]
					datastore.waypoints.append(point)
					return True
		if 'q' in query:
			m = re.search("^([0-9\.-]+),([0-9\.-]+)", query['q'][0])
			if m:
				point = GpxWaypoint(float(m.group(1)), float(m.group(2)))
				datastore.waypoints.append(point)
				return True
		ui.error(_("This Google URL cannot be imported because it does not specify the latitude and longitude."))
	
	ui.error(_("The format of the URL (%s) is not recognized.") % url)
	return False

# See: http://stackoverflow.com/questions/748324/python-convert-those-tinyurl-bit-ly-tinyurl-ow-ly-to-full-urls
def expand_short_url(url):
	f = urlopen(url)
	return f.geturl()
	
