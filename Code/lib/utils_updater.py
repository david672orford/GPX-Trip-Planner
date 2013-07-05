# utils_updater.py
# Copyright 2013, Trinity College Computing Center
# Last modified: 15 January 2013

# This package contains functions used for automatic updating of
# a program. The way it works is as follows:
# * The program is distributed as a Tar file.
# * The Tar file also contains an XML file with version information
# * The PackageUpdater class contains a download() method which downloads
#   the Tar file and unpack it into a staging area.
# * The install() method is called at program exit. It moves the running
#   version aside and moves the new version from the staging area to the
#   final location.

import tarfile
import shutil
import os
import sys
import string
import re
import xml.etree.cElementTree as ET
import stat

# Load the XML file which contains the package's version information.
def load_package_info(filename):
	tree = ET.parse(filename)
	package_info = {}
	package_info['display_version'] = tree.find("DisplayVersion").text
	package_info['update_version'] = string.atoi(tree.find("UpdateVersion").text)
	package_info['url'] = tree.find("DistribDirURL").text
	return package_info
	
# This class is used to update directories full of files (known as packages) by
# downloading an XML information file and (if there is a new version
# available) downloading it an unpacking it into a staging area (update_dir).
# When the install() method is called, the new version is moved into place
# and the old version is relegated to the staging area where it is kept
# in a numbered directory.
class PackageUpdater:
	def __init__(self, package_dir, update_dir, show_status):
		self.package_dir = package_dir
		self.update_dir = update_dir
		self.show_status = show_status

		self.package_dir_basename = os.path.basename(self.package_dir)
		self.package_info_filename = "%s_info.xml" % self.package_dir_basename

	# Remove a directory and all of its contents. This function,
	# unlike os.rmtree(), will remove read-only files.
	def rmtree_robust(self, topdir):
		for dir, subdirs, files in os.walk(topdir, topdown=False):
			for file in files:
				filename = os.path.join(dir, file)
				try:
					os.remove(filename)
				except:
					os.chmod(filename, stat.S_IWUSR)
					os.remove(filename)
			for subdir in subdirs:
				os.rmdir(os.path.join(dir, subdir))
		os.rmdir(topdir)
	
	def download(self):
		# Learn from whence to download the update.
		current_package_info = load_package_info(os.path.join(self.package_dir, self.package_info_filename))
	
		# Download the information file from the update.
		tempfile = os.path.join(self.update_dir, self.package_info_filename)
		self.download_file("%s/%s" % (current_package_info['url'], self.package_info_filename), tempfile)
		new_package_info = load_package_info(tempfile)
		os.remove(tempfile)
	
		# See if the update is newer than what is installed.
		if new_package_info['update_version'] == current_package_info['update_version']:
			self.show_status(_("No update necessary: this is already the latest version"))
			return False
		elif new_package_info['update_version'] < current_package_info['update_version']:
			self.show_status(_("No update necessary: you are running a not-yet-released version"))
			return False
		else:		# is newer
			# Download the tarfile containing the new version
			tarfile_name = "%s/%s.tar.gz" % (self.update_dir, self.package_dir_basename)
			if not os.path.exists(self.update_dir):
				os.makedirs(self.update_dir)
			self.download_file("%s/%s.tar.gz" % (new_package_info['url'], self.package_dir_basename), tarfile_name)
	
			# Open it
			tarobj = tarfile.open(tarfile_name, "r")
	
			# Make sure it will unpack into a single directory of the proper name.
			self.show_status(_("Verifying new version..."))
			ok_expr = re.compile("^%s/" % self.package_dir_basename)
			for filename in tarobj.getnames():
				#print filename
				if not ok_expr.search(filename) and filename != self.package_dir_basename:
					raise Exception("Illegal file name: %s" % filename)
	
			# Unpack the tar file, replacing any files previously unpacked.
			self.show_status(_("Unpacking new version..."))
			unpacks_into = os.path.join(self.update_dir, self.package_dir_basename)
			if os.path.exists(unpacks_into):
				self.rmtree_robust(unpacks_into)
			tarobj.extractall(self.update_dir)
	
			# Delete the tarfile
			tarobj = None
			os.remove(tarfile_name)

			return True
	
	def download_file(self, url, save_as):
		import urllib2
		self.show_status(_("Downloading %s") % url)
		http = urllib2.urlopen(url)
		save_file = open("%s.tmp" % save_as, "wb")
		bytecount=0
		while True:
			data = http.read(16384)
			if not data:
				break
			bytecount += len(data)
			save_file.write(data)
			self.show_status(_("Downloading {url}: {bytecount} bytes").format(url=url, bytecount=bytecount))
		save_file.close()
		if os.path.exists(save_as):
			os.remove(save_as)
		os.rename("%s.tmp" % save_as, save_as)
	
	def install(self):
		print "Moving updated %s into place..." % self.package_dir_basename

		# If there is already a version installed,
		if os.path.exists(self.package_dir):
			# get information about current version
			package_info = load_package_info(os.path.join(self.package_dir, self.package_info_filename))

			# move current version out of the way
			old_path = "%s-old" % self.package_dir
			if os.path.exists(old_path):
				self.rmtree_robust(old_path)
			os.rename(self.package_dir, old_path)

		# move new version into place
		temp = "%s/%s" % (self.update_dir, self.package_dir_basename)
		print " %s->%s" % (temp, self.package_dir)
		os.rename(temp, self.package_dir)

		# The update_dir may or may not yet be empty.
		try:
			os.rmdir(self.update_dir)
		except OSError:
			pass

		# If the new version contains a Python script to be run post-upgrade, run it now.
		updater = "%s/%s_updater.py" % (self.package_dir, self.package_dir_basename)
		if os.path.exists(updater):
			print "Running %s's updater..." % self.package_dir_basename
			saved_cwd = os.getcwd()
			os.chdir(self.package_dir)
			try:
				updater_code = compile(open(updater).read(), updater, 'exec')
				exec(updater_code, globals(), {'package_dir':self.package_dir, 'update_dir':self.update_dir})
			except Exception as e:
				print "Updater failed:", e
			os.chdir(saved_cwd)

		print "Done."

# For the simple case of updating a package containing the application and 
# possibly a second package containing the runtime.
#
# show_status -- a function for displaying progress messages
def download_simple_update(show_status):
	app_dir = sys.path[0]
	update_dir = os.path.join(os.path.dirname(app_dir), "updater")
	if not os.path.exists(update_dir):
		os.makedirs(update_dir)

	# List of updated packages in the staging area, ready to install
	updaters = []

	# Main package
	updater = PackageUpdater(app_dir, update_dir, show_status)
	if updater.download():
		updaters.append(updater)

	# Win32 and MacOSX need a Python runtime
	for runtime in ("Win32_Runtime", "MacOSX_Runtime"):
		runtime_path = os.path.join(app_dir, "..", runtime)
		if os.path.exists(runtime_path):
			updater = PackageUpdater(runtime_path, update_dir, show_status)
			if updater.download():
				updaters.append(updater)

	# If updates were found and we got as far as here,
	if len(updaters) > 0:
		show_status(_("New version is ready to use. Please restart program."))
		return updaters
	else:
		os.rmdir(update_dir)
		return []

# Call this after the main loop exits. Pass it the value returned
# from download_simple_update().
def install_updates(updated_packages):
	for update in updated_packages:
		update.install()

	update_dir = os.path.join(os.path.dirname(sys.path[0]), "updater")
	if os.path.exists(update_dir):
		os.rmdir(update_dir)

