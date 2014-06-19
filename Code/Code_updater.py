# Code/Code_updater.py
# Last modified: 8 August 2013
# 
# package_dir points to the Code directory
# saved_cwd is the directory with the user's data files
# The actual current directory will be package_dir.

import os
import sys
import shutil
import stat

print "package_dir:", package_dir
print "saved_cwd:", saved_cwd

#=============================================================================
# Launchers
#=============================================================================

# Update Win32 launcher (if it is already installed)
if sys.platform == "win32":
	print "Updating Win32 launcher..."

	if os.path.exists("../gpx-trip-planner.exe"):
		os.rename("../gpx-trip-planner.exe", "../Code-old/gpx-trip-planner-old.exe")
	shutil.copy2("launchers/win32/gpx-trip-planner.exe", "..")

	if os.path.exists("../desktop.ini"):
		os.system("attrib -s -h ..\\desktop.ini")
	shutil.copy2("launchers/win32/desktop.ini", "..")
	os.system("attrib +s ..")
	os.system("attrib +h +s ..\\desktop.ini")


