#! /usr/bin/python
# coding=utf-8
# Last modified: 10 August 2012
#
# Wrapper for the csv module which converts Python Unicode strings to UTF-8
# before passing them through the CSV reader and writer and then converts them
# back to Python Unicode strings.
#

import csv

class reader:
	def __init__(self, iterable):
		self.reader = csv.reader(self.encoder(iterable))

	def __iter__(self):
		return self

	# This converts the row back from UTF-8 to Unicode after it has been parsed.
	def next(self):
		return [unicode(cell, 'utf-8') for cell in self.reader.next()]

	# This converts the lines from Unicode to UTF-8 as they are read.
	def encoder(self, data):
		for line in data:
			yield line.encode('utf-8')

class writer:
	def __init__(self, fh):
		self.fh = fh
		# Create a writer which uses this object's write() method
		# to do the actual writing.
		self.writer = csv.writer(self)

	# Convert the row cells from ordinary Python strings or Python Unicode 
	# strings to UTF-8 and pass them to csv.writerow().
	def writerow(self, row):
		row = [cell.encode('utf-8') for cell in row]
		self.writer.writerow(row)

	# Take the line (which is in UTF-8 format), convert it to a Python Unicode
	# string, and send it to the output.
	def write(self, line):
		self.fh.write(line.decode('utf-8'))	# probably same as unicode(line,"utf-8")

if __name__ == "__main__":
	import codecs

	csv_writer = writer(codecs.open("test.csv", "wb", "utf-8"))
	csv_writer.writerow(["One","Two","Three"])
	csv_writer.writerow(["1","2","3"])
	csv_writer.writerow(["4","5","6"])
	csv_writer.writerow([u"Давид",u"Иван",u"Володя"])
	del csv_writer

	csv_reader = reader(codecs.open("test.csv", "rb", "utf-8"))
	for row in csv_reader:
		print row

