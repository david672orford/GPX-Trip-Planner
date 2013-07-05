#! /usr/bin/python
# address_processor.py
# Last modified: 18 December 2012

import string
import re

#=============================================================================
# Split a formatted address into parts
#=============================================================================

# For example:
#  split_address("John Smith\n123 Main St\nN Anytown\nCT\n00001")
# returns:
#  {
#  'Last Name':    'Smith',
#  'First Name':   'John',
#  'House Number': '123',
#  'Street':       'Main Street',
#  'Town':         'North Anytown,
#  'State':        'CT',
#  'ZIP':          '00001',
#  }
#
def split_address(address):
	#print "split_address(\"%s\")" % address

	# Break the address into lines, remove leading and trailing
	# whitespace from each line.
	lines = []
	for line in address.split("\n"):
		line = re.sub('^\s+', '', line)
		line = re.sub('\s+$', '', line)
		if line:	# if not left empty,
			#print "  \"%s\"" % line
			lines.append(line)

	# Place to store address components
	components = {}

	# Name
	if lines:
		if not re.match('^\d+ ', lines[0]):		# if no house number yet,
			name = lines.pop(0)
			components.update(split_name(name))

	# House number and street
	if lines:
		temp = split_house_street_apt(lines[0])
		if temp is not None:
			components.update(temp)
			lines.pop(0)

	# Town
	if lines:
		temp = split_town_state_zip(lines[0])
		if temp is not None:
			components.update(temp)
			lines.pop(0)

	return components

def split_name(name):
	components = {}
	name = re.sub('^((Mr\.?)|(Mrs\.)|(Ms\.)) ', '', name, re.IGNORECASE)
	match = re.match('^([^,]+), ?(.*)', name)
	if match:
		components['Last Name'] = match.group(1)
		components['First Name'] = match.group(2)
	else:
		name_words = name.split(' ')
		components['Last Name'] = name_words[-1]
		components['First Name'] = ' '.join(name_words[0:-1])
	return components

re_address1 = re.compile("^(\d+\S*) (.+)$")
re_apartment1 = re.compile("^(.*) #([^#]+)$")	# "1 Main St #C"
re_apartment2 = re.compile("^(.*), Apt (.+)$")	# "1 Main St, Apt C"
def split_house_street_apt(text):
	m = re_address1.search(text)
	if m:
		components = {}
		components['House Number'] = m.group(1)
		components['Street'] = m.group(2)
		while True:
			m = re_apartment1.search(components['Street'])
			if not m:
				m = re_apartment2.search(components['Street'])
			if not m:
				break
			components['Street'] = m.group(1)
			components['Apartment Number'] = m.group(2)
		components['Street'] = disabbreviate_street(components['Street'])
		return components
	else:
		return None

def split_town_state_zip(text):
	match = re.match('^([^,]+)(?:, *(\w+)(?: (\d\d\d\d\d(?:-\d\d\d\d)?))?)?', text)
	if match:
		components = {}
		town = match.group(1)
		components['Town'] = disabbreviate_town(town)
		if match.group(2):
			components['State'] = match.group(2)
		if match.group(3):
			components['ZIP'] = match.group(3)
		return components
	else:
		return None

def split_schema_person(item):
	components = {}

	temp = split_name(item['name'])
	if temp is not None:
		components.update(temp)

	temp = split_house_street_apt(item['streetAddress'])
	if temp is not None:
		components.update(temp)

	components['Town'] = disabbreviate_town(item['addressLocality'])
	components['State'] = item['addressRegion']
	components['ZIP']  = item['postalCode']
	components['Phone Number'] = item['telephone']

	return components

#=============================================================================
#
#=============================================================================

# Directional prefixes of street and town names
# Applies only to a run of one or more words starting with the first
prefix_table = {
	'N':'North',
	'Ne':'Northeast',
	'E':'East',
	'Se':'Southeast',
	'S':'South',
	'Sw':'Southwest',
	'W':'West',
	'Nw':'Northwest',
	}
for i in prefix_table.values():
	prefix_table[i] = i

# Suffixes of street names
# Applies only to a run of one or more words starting with the last
suffix_table = {
	'Ext':'Extension',
	'N':'North',
	'S':'South',
	'E':'East',
	'W':'West',
	}
for i in suffix_table.values():		# add unabbreviated versions
	suffix_table[i] = i

# Street type, recommended abbreviation, followed by other abbreviations
street_types = [
	# From USPS list
	['Alley','Aly','Allee','Ally'],
	['Annex','Anx','Anex','Annx'],
	['Arcade','Arc'],
	['Avenue','Ave','Av','Aven','Avenu','Avn','Avnue'],
	['Bayoo','Byu','Bayou'],
	['Beach','Bch'],
	['Bend','Bnd'],
	['Bluff','Blf','Bluf'],
	['Bluffs','Blfs'],
	['Bottom','Btm','Bot','Bottm'],
	['Boulevard','Blvd','Boul','Boulv'],
	['Branch','Br','Brnch'],
	['Bridge','Brg','Brdge'],
	['Brook','Brk'],
	['Brooks','Brks'],
	['Burg','Bg'],
	['Burgs','Bgs'],
	['Bypass','Byp','Bypa','Bypas','Byps'],
	['Camp','Cp','Cmp'],
	['Canyon','Cyn','Canyn','Cnyn'],
	['Cape','Cpe'],
	['Causeway','Cswy','Causway'],
	['Center','Ctr','Cen','Cent','Centr','Centre','Cnter','Cntr'],
	['Centers','Ctrs'],
	['Circle','Cir','Circ','Circl','Crcl','Crcle'],
	['Circles','Cirs'],
	['Cliff','Clf'],
	['Cliffs','Clfs'],
	['Club','Clb'],
	['Common','Cmn'],
	['Corner','Cor'],
	['Corners','Cors'],
	['Course','Crse'],
	['Court','Ct','Crt'],
	['Courts','Cts'],
	['Cove','Cv'],
	['Coves','Cvs'],
	['Creek','Crk','Ck','Cr'],
	['Crescent','Cres','Crecent','Cresent','Crscnt','Crsent','Crsnt'],
	['Crest','Crst'],
	['Crossing','Xing','Crssing','Crssng'],
	['Crossroad','Xrd'],
	['Curve','Curv'],
	['Dale','Dl'],
	['Dam','Dm'],
	['Divide','Dv','Div','Dvd'],
	['Drive','Dr','Driv','Drv'],
	['Drives','Drs'],
	['Estate','Est'],
	['Estates','Ests'],
	['Expressway','Expy','Exp','Expr','Express','Expw'],
	['Extension','Ext','Extn','Extnsn'],
	['Extensions','Exts'],
	['Fall'],
	['Falls','Fls'],
	['Ferry','Fry','Frry'],
	['Field','Fld'],
	['Fields','Flds'],
	['Flat','Flt'],
	['Flats','Flts'],
	['Ford','Frd'],
	['Fords','Frds'],
	['Forest','Frst','Forests'],
	['Forge','Frg','Forg'],
	['Forges','Frgs'],
	['Fork','Frk'],
	['Forks','Frks'],
	['Fort','Ft','Frt'],
	['Freeway','Fwy','Freewy','Frway','Frwy'],
	['Garden','Gdn','Gardn','Grden','Grdn'],
	['Gardens','Gdns','Grdns'],
	['Gateway','Gtwy','Gatewy','Gatway','Gtway'],
	['Glen','Gln'],
	['Glens','Glns'],
	['Green','Grn'],
	['Greens','Grns'],
	['Grove','Grv','Grov'],
	['Groves','Grvs'],
	['Harbor','Hbr','Harb','Harbr','Hrbor'],
	['Harbors','Hbrs'],
	['Haven','Hvn','Havn'],
	['Heights','Hts','Height','Hgts','Ht'],
	['Highway','Hwy','Highwy','Hiway','Hiwy','Hway'],
	['Hill','Hl'],
	['Hills','Hls'],
	['Hollow','Holw','Hllw','Hollows','Holws'],
	['Inlet','Inlt'],
	['Island','Is','Islnd'],
	['Islands','Iss','Islnds'],
	['Isle','Isles'],
	['Junction','Jct','Jction','Jctn','Junctn','Juncton'],
	['Junctions','Jcts','Jctns'],
	['Key','Ky'],
	['Keys','Kys'],
	['Knoll','Knl','Knol'],
	['Knolls','Knls'],
	['Lake','Lk'],
	['Lakes','Lks'],
	['Land'],
	['Landing','Lndg','Lndng'],
	['Lane','Ln','La','Lanes'],
	['Light','Lgt'],
	['Lights','Lgts'],
	['Loaf','Lf'],
	['Lock','Lck'],
	['Locks','Lcks'],
	['Lodge','Ldg','Ldge','Lodg'],
	['Loop','Loops'],
	['Mall'],
	['Manor','Mnr'],
	['Manors','Mnrs'],
	['Meadow','Mdw'],
	['Meadows','Mdws','Medows'],
	['Mews'],
	['Mill','Ml'],
	['Mills','Mls'],
	['Mission','Msn','Missn','Mssn'],
	['Motorway','Mtwy'],
	['Mount','Mt','Mnt'],
	['Mountain','Mtn','Mntain','Mntn','Mountin','Mtin'],
	['Mountains','Mtns','Mntns'],
	['Neck','Nck'],
	['Orchard','Orch','Orchrd'],
	['Oval','Ovl'],
	['Overpass','Opas'],
	['Park','Pk','Prk'],
	['Parks'], # ,'Park'],
	['Parkway','Pkwy','Parkwy','Pkway','Pky'],
	['Parkways','Pkwy','Pkwys'],
	['Pass'],
	['Passage','Psge'],
	['Path','Paths'],
	['Pike','Pikes'],
	['Pine','Pne'],
	['Pines','Pnes'],
	['Place','Pl'],
	['Plain','Pln'],
	['Plains','Plns','Plaines'],
	['Plaza','Plz','Plza'],
	['Point','Pt'],
	['Points','Pts'],
	['Port','Prt'],
	['Ports','Prts'],
	['Prairie','Pr','Prarie','Prr'],
	['Radial','Radl','Rad','Radiel'],
	['Ramp'],
	['Ranch','Rnch','Ranches','Rnchs'],
	['Rapid','Rpd'],
	['Rapids','Rpds'],
	['Rest','Rst'],
	['Ridge','Rdg','Rdge'],
	['Ridges','Rdgs'],
	['River','Riv','Rivr','Rvr'],
	['Road','Rd'],
	['Roads','Rds'],
	['Route','Rte'],
	['Row'],
	['Rue'],
	['Run'],
	['Shoal','Shl'],
	['Shoals','Shls'],
	['Shore','Shr','Shoar'],
	['Shores','Shrs','Shoars'],
	['Skyway','Skwy'],
	['Spring','Spg','Spng','Sprng'],
	['Springs','Spgs','Spngs','Sprngs'],
	['Spur'],
	['Spurs','Spur'],
	['Square','Sq','Sqr','Sqre','Squ'],
	['Squares','Sqs','Sqrs'],
	['Station','Sta','Statn','Stn'],
	['Stravenue','Stra','Strav','Strave','Straven','Stravn','Strvn','Strvnue'],
	['Stream','Strm','Streme'],
	['Street','St','Str','Strt'],
	['Streets','Sts'],
	['Summit','Smt','Sumit','Sumitt'],
	['Terrace','Ter','Terr'],
	['Throughway','Trwy'],
	['Trace','Trce','Traces'],
	['Track','Trak','Tracks','Trk','Trks'],
	['Trafficway','Trfy'],
	['Trail','Trl','Tr','Trails','Trls'],
	['Tunnel','Tunl','Tunel','Tunls','Tunnels','Tunnl'],
	['Turnpike','Tpke','Tpk','Trnpk','Trpk','Turnpk'],
	['Underpass','Upas'],
	['Union','Un'],
	['Unions','Uns'],
	['Valley','Vly','Vally','Vlly'],
	['Valleys','Vlys'],
	['Viaduct','Via','Vdct','Viadct'],
	['View','Vw'],
	['Views','Vws'],
	['Village','Vlg','Vill','Villag','Villg','Villiage'],
	['Villages','Vlgs'],
	['Ville','Vl'],
	['Vista','Vis','Vist','Vst','Vsta'],
	['Walk'],
	['Walks','Walk'],
	['Wall'],
	['Way','Wy'],
	['Ways'],
	['Well','Wl'],
	['Wells','Wls'],

	# Not in USPS list
	["Bank", "Bk"],
	]

# Create an easily searchable version of the street types table.
# The keys will be words and word abbreviations that may be
# encountered. The cooresponding values are the unabbreviated forms.
words_table = { }
for x in street_types:						# alternative abbreviations first
	for y in x[2:]:
		words_table[y] = x[0]
for x in street_types:						# unabbreviated form and preferred abbreviation
	words_table[x[0]] = x[0]
	if len(x) > 1:
		words_table[x[1]] = x[0]

# Create a table for abbreviating street names.
street_abbreviator_table = {}
for x in street_types:
	if len(x) > 1:
		street_abbreviator_table[x[0]] = x[1]

# Use the above tables to disabbreviate a street name.
#
# If phonebook_format is True, then street names which do not end
# in a recognized suffix such as "Street" or "Drive" will have
# "Street" added.
#
# If you pass an empty string to this function, it will return an
# empty string.
def disabbreviate_street(street, phonebook_format=False):
	street = string.capwords(street)		# good idea?
	words = street.split()					# split into words, discarding extra whitespace

	if len(words) == 0:
		return ""

	# Use prefix table to disabbreviate words starting from the left until we 
	# hit a word that his not a prefix (whether abbreviated or not).
	prefixes = []
	while words and prefix_table.has_key(words[0]):
		prefixes.append(prefix_table[words.pop(0)])

	# Use suffix table to disabbreviate words starting from the right until we 
	# hit a word that his not a prefix (whether abbreviated or not).
	suffixes = []
	while words and suffix_table.has_key(words[-1]):
		suffixes.insert(0, suffix_table[words.pop(-1)])

	# "St" at the beginning of the street name means "Saint". (At the
	# end it means "Street".)
	if len(words) >= 2 and words[0] == 'St':	# "St Bernard" --> "Saint Bernard"
		words[0] = 'Saint'

	# Run all remaining words throught the general table.
	new_words = []
	for w in words:
		new_words.append(words_table.get(w,w))

	words = prefixes + new_words

	# In phone book mode:
	# "Park Drive" remains the same
	# "City Arcade" remains the same (since "Arcade" is a street suffix), but
	# "Arcade" becomes "Arcade Street"
	if phonebook_format and ( len(words) < 2 or not words_table.has_key(words[-1]) ):
		words.append("Street")

	words.extend(suffixes)

	return ' '.join(words)

def abbreviate_street(street):
	street = re.sub('\s+', ' ', street)
	street = re.sub('\. ', ' ', street)
	words = street.split(' ')
	new_words = []
	for w in words:
		new_words.append(street_abbreviator_table.get(w, w))
	return ' '.join(new_words)

def disabbreviate_town(town):
	town = re.sub('\s+', ' ', town)
	town = re.sub('\. ', ' ', town)
	town = string.capwords(town)
	words = town.split(' ')
	new_words = []
	for w in words:
		new_words.append(prefix_table.get(w, w))
	return ' '.join(new_words)

states_table = {
	'Connecticut':'CT',
	'Maine':'ME',
	'Massachusetts':'MA',
	'New Hampshire':'NH',
	'New Jersey':'NJ',
	'New York':'NY',
	'Pennsylvania':'PA',
	'Rhode Island':'RI',
	'Texas':'TX',
	'Vermont':'VT',
	}

def abbreviate_state(state):
	if states_table.has_key(state):
		return states_table[state]
	else:
		return state

if __name__ == "__main__":
	import sys
	if len(sys.argv) == 3 and sys.argv[1] == 'parse':
		print split_address(sys.argv[2])
	elif len(sys.argv) == 3 and sys.argv[1] == 'street':
		print disabbreviate_street(sys.argv[2], True)
	elif len(sys.argv) == 2 and sys.argv[1] == 'test1':
		print split_address("""
			Mr. John Smith
			123 Main St, Apt 15
			Anytown, ST 00000
			""")
	elif len(sys.argv) == 2 and sys.argv[1] == 'test2':
		print split_house_street_apt("19 Princeton St, Apt 1")
	else:
		raise Exception


