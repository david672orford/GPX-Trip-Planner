#! /usr/bin/python
# shared_table_client.py
# Copyright 2013, Trinity College Computing Center
# Last modified: 14 June 2013
#

import xml.etree.cElementTree as ET
import urllib2
import os
import format_csv_unicode as csv

#=============================================================================
# Client Library
#=============================================================================

# Thrown for errors during syncronization
class SharedTableError(Exception):
	pass

# Thrown if the local and server formats differ
class SharedTableFormatError(SharedTableError):
	pass

class SharedTableConflict:
	def __init__(self, index, obj):
		assert index > 0, "Conflict on row 0 should not be possible."
		self.obj = obj
		self.index = index
		self.resolved = False

	# Return the index of the row in conflict and the row contents from the server.
	def get_row(self):
		reader = csv.reader([self.obj.text])
		row = reader.next()
		return (self.index, row)

	def resolve(self):
		assert not self.resolved
		self.resolved = True

	def unresolve(self):
		assert self.resolved
		self.resolved = False

class SharedTable:
	def __init__(self, local_filename, debug=0):
		self.debug_level = debug
		self.debug(1, "SharedTable.__init__()")

		# Load the local store into an ElementTree
		self.local_filename = local_filename
		self.xml = ET.parse(self.local_filename)

		# Find the remote repository
		self.url = self.xml.find("repository/url").text
		#for i in self.xml.getroot():
		#	print "<%s>" % i.tag
		self.xml_pulled_version = self.xml.find("repository/pulled_version")
		realm = self.xml.find("repository/realm").text
		username = self.xml.find("repository/username").text
		password = self.xml.find("repository/password").text

		# Prepare to authenticate oneself.
		auth_handler = urllib2.HTTPDigestAuthHandler()
		auth_handler.add_password(
			uri=self.url,
			realm=realm,
			user=username,
			passwd=password
			)
		opener = urllib2.build_opener(auth_handler)
		urllib2.install_opener(opener)

		# Find row containers
		self.xml_conflict_rows = self.find_or_create("conflict_rows")
		self.xml_rows = self.find_or_create("rows")
		self.xml_new_rows = self.find_or_create("new_rows")

		# These keep track of the data which the application has pulled out 
		# of the local store.
		self.read_rows = None
		self.read_conflicts = None
		self.read_new_rows = None

		self.new_table = False

	# Locate the specified container tag and return a reference to it.
	# If there is no such container tag, create one and return a reference
	# to the newly-created tag.
	def find_or_create(self, tag):
		self.debug(2, "Searching for <%s>" % tag)
		obj = self.xml.find(tag)
		if obj == None:
			self.debug(1, "Creating <%s>" % tag)
			obj = ET.SubElement(self.xml.getroot(), tag)
			obj.text = '\n'
			obj.tail = '\n'
		return obj

	#====================================================
	# For debugging
	#====================================================
	def debug(self, level, message):
		if self.debug_level >= level:
			print message

	def dump(self):
		if self.debug_level > 0:
			import sys
			assert self.xml
			print "====== Local Store ======"
			self.xml.write(sys.stdout)
			print

	#====================================================
	# Find all of the <row>s in a particular container
	# and return them in a hash keyed by the value of
	# the id attribute.
	#====================================================
	def index_rows(self, container):
		hash = {}
		for i in list(container):
			assert i.tag == "row"
			id = int(i.get("id"))
			hash[id] = i
		return hash

	#====================================================
	# Send an XML request to the server and receive
	# an XML response.
	#====================================================
	def post_xml(self, xml):
		data = ET.tostring(xml, encoding='utf-8')
		self.debug(1, "====== POSTed XML ======")
		self.debug(1, data)

		req = urllib2.Request(self.url, data, {'Content-Type':'application/xml'})
		try:
			http = urllib2.urlopen(req)
			resp_text = http.read()
		except urllib2.HTTPError as e:
			raise SharedTableError("%s:\n%s" % (str(e), e.read()))
		except Exception as e:
			raise SharedTableError(str(e))

		self.debug(1, "====== Response XML ======")
		self.debug(1, resp_text)

		return ET.XML(resp_text)

	#====================================================
	# Ask the server to create the shared table which
	# is described by this client object. This will fail
	# (and return False), if the table already exists
	# on the server.
	#====================================================
	def create_table(self):
		self.debug(1, "SharedTable.create_table()")

		top = ET.Element('request')
		top.text = '\n'
		child = ET.SubElement(top, 'type')
		child.text = 'create'
		child.tail = '\n'

		resp = self.post_xml(top)

		result = resp.find('result').text
		self.debug(1, "Result: %s" % result)

		error_message = resp.find('error_message')
		if error_message:
			sys.stderr.write("Error on server: %s\n", error_message)

		self.new_table = True

		return result == "OK"

	#====================================================
	# Save the current state of the local store to file.
	#====================================================
	def save(self):
		self.debug(1, "SharedTable.save(): save to \"%s\"..." % self.local_filename)
		(base, ext) = os.path.splitext(self.local_filename)
		temp = "%s.tmp" % base
		backup = "%s.bak" % base
		self.xml.write(temp, encoding='utf-8')
		if os.path.exists(self.local_filename):
			if os.path.exists(backup):
				os.remove(backup)
			os.rename(self.local_filename, backup)
		os.rename(temp, self.local_filename)

	#====================================================
	# Pull the latest changes down from the server.
	#====================================================
	def pull(self):
		self.debug(1, "SharedTable.pull()")

		# Build XML request
		top = ET.Element('request')
		top.text = '\n'
		child = ET.SubElement(top, 'type')
		child.text = 'pull'
		child.tail = '\n'
		child = ET.SubElement(top, 'pulled_version')
		child.text = self.xml_pulled_version.text
		child.tail = '\n'

		# Send request and parse the response
		resp = self.post_xml(top)

		# Index the rows already in our copy.
		conflict_rows_by_id = self.index_rows(self.xml_conflict_rows)
		rows_by_id = self.index_rows(self.xml_rows)

		# Take the received rows and use them to update our local copy
		count_changes = 0
		count_conflicts = 0
		for row in resp.find('rows'):
			assert row.tag == 'row'
			id = int(row.get('id'))
			version = row.get('version')
			self.debug(2, "Received row (id=%d, version=%s): %s" % (id, version, row.text))
			assert id != 0 or int(version) == 1, "Row with ID 0 may not advance beyond version 1."

			# already known to be in conflict
			if conflict_rows_by_id.has_key(id):
				self.debug(2, "  Known conflict")
				#count_conflicts += 1	# do this below only if also a change
				existing = conflict_rows_by_id[id]
				if version != existing.get('version'):			# If there were furthur changes,
					existing['version'] = version				# accept them.
					existing.text = row.text
					count_changes += 1
					count_conflicts += 1

			# If this row is in the repository,
			elif rows_by_id.has_key(id):
				existing = rows_by_id[id]
				if id == 0:
					if existing.text != row.text:
						raise SharedTableFormatError
				elif version == existing.get('version'):
					self.debug(2, "  Not changed on server")
				else:
					self.debug(2, "  Changed on server")
					assert id != 0, "Row with ID 0 should not have changed."
					count_changes += 1
					if existing.attrib.has_key('modified'):		# new conflict
						self.debug(1, "    new conflict")
						count_conflicts += 1
						self.xml_conflict_rows.append(row)
					else:										# non-conflicting change
						self.debug(2, "    updated")
						existing.attrib['version'] = version
						existing.text = row.text

			# completely new row
			else:			
				self.debug(2, "  New row from server")
				self.xml_rows.append(row)
				count_changes += 1

		# Copy the version number from the response to the local store.
		self.xml_pulled_version.text = resp.find('version').text

		assert count_changes >= count_conflicts, "count_changes=%d, count_conflicts=%d" % (count_changes, count_conflicts)
		return count_changes, count_conflicts

	@staticmethod
	def add_row(parent, id, version, data):
		child = ET.SubElement(parent, 'row')
		child.tail = '\n'
		child.attrib = {
			'id':id,
			'version':str(version),
			}
		child.text = data

	#====================================================
	# Push any modified recoreds up to the server.
	#====================================================
	def push(self):
		self.debug(1, "SharedTable.push()")

		count_changes = 0
		count_conflicts = 0

		# Build XML request
		top = ET.Element('request')
		top.text = '\n'
		child = ET.SubElement(top, 'type')
		child.text = 'push'
		child.tail = '\n'

		# Push any changes to existing rows
		req_rows = ET.SubElement(top, 'rows')
		req_rows.text = '\n'
		req_rows.tail = '\n'
		for row in list(self.xml_rows):
			id = int(row.get('id'))
			if id == 0:
				assert int(row.get('version')) == 1, "Row with ID 0 must never be modified."
				self.add_row(req_rows, row.get('id'), 1, row.text)
			elif row.attrib.has_key('modified'):
				self.debug(2, "Row %s is modified: %s" % (row.get('id'), row.text))
				count_changes += 1
				self.add_row(req_rows, row.get('id'), int(row.get('version')) + 1, row.text)

		# Push new rows
		req_new_rows = ET.SubElement(top, 'new_rows')
		req_new_rows.text = '\n'
		req_new_rows.tail = '\n'
		for row in list(self.xml_new_rows):
			self.debug(2, "New row: %s" % row.text)
			count_changes += 1
			child = ET.SubElement(req_new_rows, 'row')
			child.text = row.text
			child.tail = '\n'

		# Make the request only if it is non-empty
		if count_changes > 0:
			count_changes_accepted = 0

			# Send request and parse the response
			resp = self.post_xml(top)
	
			result = resp.find('result').text
			if result == "FORMAT_CONFLICT":
				raise SharedTableFormatError
			elif result != "OK":
				raise SharedTableError

			# Remove the modified attribute from rows for which the change
			# was accepted and bump the version number.
			rows_by_id = self.index_rows(self.xml_rows)
			for r_row in list(resp.find("modified_rows")):
				assert r_row.tag == "row"
				id = int(r_row.get('id'))
				self.debug(1, "Row successfully modified: %d" % id)
				row = rows_by_id[id]
				del row.attrib['modified']
				row.attrib['version'] = str(int(row.get('version')) + 1)
				count_changes_accepted += 1
	
			# Accept the IDs which the server has assigned to the new rows
			# and move them to the end of the main list of rows.
			r_new_rows = list(resp.find("new_rows"))
			for row in list(self.xml_new_rows):
				assert row.tag == "row"
				r_row = r_new_rows.pop(0)
				assert r_row.tag == "row"
				id = r_row.get('id')
				self.debug(1, "New row received id: %s" % id)
				child = ET.SubElement(self.xml_rows, "row")
				child.attrib = {'id':id, 'version':'1'}
				child.text = row.text
				child.tail = "\n"
				self.xml_new_rows.remove(row)
				count_changes_accepted += 1

			count_conflicts = int(resp.find("conflict_count").text)
			self.debug(1, "Conflict count: %d" % count_conflicts)

			assert (count_changes_accepted + count_conflicts) == count_changes
	
			# An optimization to (most of the time) prevent the changes we push
			# from coming right back at us the next time we pull.
			#	
			# If one or more of our changes took and the version number that the
			# table now has on the server is one greater than the last one that
			# we list pulled, then we and only we made it increase. That means
			# that we can safely bump the version number on our side without
			# doing a pull.
			if count_changes_accepted > 0:
				tver = int(resp.find('version').text)
				if tver == (int(self.xml_pulled_version.text) + 1):
					self.debug(1, "No other pushes since last pull, bumping tver.")
					self.xml_pulled_version.text = str(tver)
				else:
					self.debug(1, "There has been an intervening push, leaving tver.")
			else:
				self.debug(1, "No changes were made.")

		assert count_changes >= count_conflicts, "count_changes=%d, count_conflicts=%d" % (count_changes, count_conflicts)
		return count_changes, count_conflicts

	#====================================================
	# Return an object which will return all of the rows
	# in id order.
	# Remember the ids of the rows since the caller will
	# not receive them. Also remember which of the rows
	# have conflicts, since the caller may ask later by
	# calling get_conflicts().
	#====================================================
	def csv_reader(self):
		self.debug(1, "SharedTable.csv_reader()")

		rows = self.index_rows(self.xml_rows)
		conflict_rows = self.index_rows(self.xml_conflict_rows)
		self.csv_rows = []
		self.csv_conflicts = []
		self.csv_new_rows = []

		# CSV data that will need to be parsed
		data = []

		# Add those rows which are already on the server to data[].
		# Take special note of any that are in conflict with the server
		# versions.
		index = 0
		for key in sorted(rows.keys()):
			self.debug(1, "CSV server row: %s" % rows[key].text)
			self.csv_rows.append(rows[key])
			data.append(rows[key].text)
			if conflict_rows.has_key(key):
				self.csv_conflicts.append(SharedTableConflict(index, conflict_rows[key]))
			index += 1

		# Add the new rows which we have not yet added to the server to the very end.
		for row in list(self.xml_new_rows):
			self.debug(2, "CSV new row: %s" % row.text)
			self.csv_new_rows.append(row)
			data.append(row.text)

		return csv.reader(data)

	#====================================================
	# Return an object to which the caller can writerow()
	# the rows return by csv_reader() as then now are.
	#====================================================
	def csv_writer(self):
		self.debug(1, "SharedTable.csv_writer()")

		# Make sure csv_reader() has been called.
		assert self.csv_rows != None
		assert self.csv_conflicts != None

		# The caller has previously told us if any conflicts will be resolved
		# by this write. Apply this stored up information to the local store.
		index = 0
		remain = []
		for conflict in self.csv_conflicts:
			if conflict.resolved:
				self.debug(2, "Conflict %d resolved" % index)
				# Change the version number of our copy of the row in order to indicate
				# that it is a modified copy of the conflicting row. (The modifictions
				# resolve the conflict.)
				self.csv_rows[conflict.index].attrib['version'] = conflict.obj.attrib['version']
				self.xml_conflict_rows.remove(conflict.obj)
			else:
				self.debug(2, "Conflict %d not resolved" % index)
				remain.append(conflict)
			index += 1
		self.csv_conflicts = remain

		self.csv_overall_index = 0
		self.csv_rows_index = 0
		self.csv_new_rows_index = 0

		# Create a CVS writer that will write lines by calling write() below.
		return csv.writer(self)

	def write(self, text):
		self.debug(1, "SharedTable.write(\"%s\")" % text)
		text = text.rstrip("\r\n")

		# Look at the index number of the row (not the ID).
		# It will fall into one of three possible ranges,
		# each of which requires a particular treatment.
		if self.csv_rows_index < len(self.csv_rows):				# Row is already on the server
			self.debug(2, "  row exists in repository")
			existing = self.csv_rows[self.csv_rows_index]
			if existing.text != text:
				self.debug(2, "    modified")
				existing.text = text
				existing.set('modified', '1')
			self.csv_rows_index += 1
		elif self.csv_new_rows_index < len(self.csv_new_rows):		# Not on server, but was already in local store
			self.debug(2, "  row exists in local store")
			existing = self.csv_new_rows[self.csv_new_rows_index]
			existing.text = text
			self.csv_new_rows_index += 1
		elif self.csv_overall_index == 0 and not self.new_table:	# Special case
			self.debug(2, "  Header row (when local store is empty)")
			# The first row of the table always specifies the column headings.
			# This special case prevents it from becoming a new row before we
			# can pull it from the repository. 
			child = ET.SubElement(self.xml_rows, 'row')
			child.attrib = {'id':'0', 'version':'1'}
			child.text = text
			child.tail = "\n"
		else:														# Entirely new
			self.debug(2, "  new row added to local store")
			child = ET.SubElement(self.xml_new_rows, 'row')
			child.text = text
			child.tail = "\n"
			# It is important to do this since there is no guarantee that the
			# user of this library will call csv_reader() before calling
			# csv_writer() again.
			self.csv_new_rows_index += 1
			self.csv_new_rows.append(child)

		self.csv_overall_index += 1

	#====================================================
	# Return the list of conflicts which were noted
	# when csv_reader() was preparing the data.
	#====================================================
	def get_conflicts(self):
		self.debug(1, "SharedTable.get_conflicts()")
		assert self.csv_conflicts != None
		return self.csv_conflicts

	#====================================================
	# Reverse the resolution of a conflict that has
	# not yet been commited to the local store (by
	# using csv_writer()). This is used to implement
	# Undo.
	#====================================================
	def unresolve_conflict(self, conflict_index):
		self.debug(1, "SharedTable.unresolve_conflict(%d)" % conflict_index)
		assert self.csv_conflicts != None
		self.csv_conflicts[conflict_index].unresolve()

	#====================================================
	# Dump the local repository
	#====================================================
	def clear_local_store(self):
		self.debug(1, "SharedTable.clear_local_store()")
		for row in list(self.xml_conflict_rows):
			self.xml_conflict_rows.remove(row)
		for row in list(self.xml_rows):
			self.xml_rows.remove(row)
		for row in list(self.xml_new_rows):
			self.xml_new_rows.remove(row)
		self.xml_pulled_version.text = '0'

#=============================================================================
# Command line client which demonstrates use of above client library
#=============================================================================
if __name__ == "__main__":
	import sys
	import codecs

	def create_client():
		if len(sys.argv) < 3:
			sys.stderr.write("Please supply the name of the STB file.\n")
			sys.exit(1)
		client = SharedTable(sys.argv[2])
		client.debug_level = 1
		return client

	if len(sys.argv) < 2:
		print "Usage: %s import <filename.stb> <filename.csv>"
		print "       %s export <filename.stb> <filename.csv>"
		sys.exit(0)


	if sys.argv[1] == "import":
		client = create_client()

		if len(sys.argv) < 4:
			sys.stderr.write("Please supply the name of the CSV file.\n")
			sys.exit(1)

		if not client.create_table():
			sys.stderr.write("Failed to create new shared table.\n")
			sys.exit(1)

		# We can't call csv_writer() until we have called this.
		client.csv_reader()
	
		reader = csv.reader(codecs.open(sys.argv[3], "rb", "utf-8"))
		writer = client.csv_writer()

		for row in reader:
			writer.writerow(row)
	
		client.push()
		client.save()

	elif sys.argv[1] == "export":
		client = create_client()

		if len(sys.argv) < 4:
			sys.stderr.write("Please supply the name of the CSV file.\n")
			sys.exit(1)

		reader = client.csv_reader()
		writer = csv.writer(codecs.open(sys.argv[3], "wb", "utf-8"))

		for row in reader:
			writer.writerow(row)

	elif sys.argv[1] == "update":
		client = create_client()

		if len(sys.argv) < 4:
			sys.stderr.write("Please supply the name of the CSV file.\n")
			sys.exit(1)

		reader = client.csv_reader()

		writer = client.csv_writer()
		file_reader = csv.reader(codecs.open(sys.argv[3], "rb", "utf-8"))
		for row in file_reader:
			writer.writerow(row)

		client.save()

	else:
		sys.stderr.write("Unrecognized subcommand: %s\n" % sys.argv[1])

# end of file
