#! /usr/bin/python
# lib/utils_gtk_merge.py
# Copyright 2013, Trinity College Computing Center
# Last modified: 4 January 2013

import gtk

class MergeDialog(gtk.Dialog):

	def __init__(self,
			title="Merge Records",
			record_labels=("Input1", "Output", "Input2"),
			field_labels=None,
			button_labels=("Cancel", "OK"),
			show_all=False,
			grey_matching=True,
			entry_width_chars=16
			):
		gtk.Dialog.__init__(self, title=title, flags=gtk.DIALOG_MODAL)

		self.record_labels = record_labels
		self.field_labels = field_labels
		self.button_labels=button_labels
		self.show_all = show_all
		self.grey_matching = grey_matching	
		self.entry_width_chars = entry_width_chars

		if len(record_labels) != 3:
			raise ValueError
		if field_labels is None:
			raise ValueError
		if len(button_labels) != 2:
			raise ValueError

		self.add_button(self.button_labels[0], 0)
		self.merge_button = self.add_button(self.button_labels[1], 1)

		self.result = None
		self.changed = None
		self.table = None

	# Load the two versions of a row into the widget
	def load(self, input1, input2, suggestions=[]):
		if len(input1) != len(self.field_labels):
			raise ValueError
		if len(input2) != len(self.field_labels):
			raise ValueError

		self.input1 = input1
		self.changed = set([])

		# Remove table from previous run.
		if self.table is not None:
			self.vbox.remove(self.table)

		# Create a new one to hold the two records, the final record, and the merge buttons.
		self.table = gtk.Table(rows=len(self.field_labels) + 1, columns=6)
		self.vbox.pack_start(self.table, expand=False, fill=False)

		# Create the table column headings
		colnum=0
		for label_text in (
				None,						# field label column
				self.record_labels[0],
				None,						# arrow column
				self.record_labels[1],
				None,						# arrow column
				self.record_labels[2]
				):
			if label_text is not None:
				label = gtk.Label(str=label_text)
				self.table.attach(label, colnum, colnum+1, 0, 1)
			colnum += 1

		# Create the table rows
		self.output_entries = []
		rownum = 1
		self.diffcount = 0
		for i in range(len(self.field_labels)):
			if self.show_all or input1[i] != input2[i]:
				label = gtk.Label(self.field_labels[i])

				# Column 1: field from input1
				entry_input1 = gtk.Entry()
				entry_input1.set_editable(False)
				entry_input1.set_width_chars(self.entry_width_chars)
				entry_input1.set_text(input1[i])
	
				# Column 2: the left-hand arrow (which points right)
				button_left_arrow = gtk.Arrow(gtk.ARROW_RIGHT, gtk.SHADOW_OUT)
				button_left = gtk.Button()
				button_left.add(button_left_arrow)
	
				# Column 3: the output selected by the user
				entry_output = gtk.Entry()
				entry_output.set_width_chars(self.entry_width_chars)
	
				# Column 4: the right-hand arrow (which points left)
				button_right_arrow = gtk.Arrow(gtk.ARROW_LEFT, gtk.SHADOW_OUT)
				button_right = gtk.Button()
				button_right.add(button_right_arrow)
	
				# Column 5: field from input2
				entry_input2 = gtk.Entry()
				entry_input2.set_editable(False)
				entry_input2.set_width_chars(self.entry_width_chars)
				entry_input2.set_text(input2[i])

				# The two buttons each copy one of the two input fields into the output field.
				button_left.connect('clicked', lambda widget, d, s: d.set_text(s.get_text()), entry_output, entry_input1)
				button_right.connect('clicked', lambda widget, d, s: d.set_text(s.get_text()), entry_output, entry_input2)

				# If this field has a conflict to be resolved, connect an event handler to detect
				# when something has been entered into the output field.
				if input1[i] != input2[i]:
					entry_output.connect('changed', self.entry_output_changed_cb, i)
				elif self.grey_matching:
					entry_input1.set_sensitive(False)
					entry_input2.set_sensitive(False)
					entry_output.set_sensitive(False)
					button_left.set_sensitive(False)
					button_right.set_sensitive(False)

				# Stuff the row into the table, cell-by-cell.	
				self.table.attach(label, 0, 1, rownum, rownum+1)
				self.table.attach(entry_input1, 1, 2, rownum, rownum+1)
				self.table.attach(button_left, 2, 3, rownum, rownum+1)
				self.table.attach(entry_output, 3, 4, rownum, rownum+1)
				self.table.attach(button_right, 4, 5, rownum, rownum+1)
				self.table.attach(entry_input2, 5, 6, rownum, rownum+1)

				# If the rows are for this column identical (which can only
				# happen if show_all is True, then copy the value into the
				# final answer cell. Otherwise, chalk this up as a difference
				# to be resolved.	
				if input1[i] == input2[i]:
					entry_output.set_text(input1[i])
				else:
					self.diffcount += 1
					if suggestions is not None and i in suggestions:
						entry_output.set_text(suggestions[i])

				self.output_entries.append(entry_output)
				rownum += 1
			else:
				self.output_entries.append(None)

		self.table.show_all()
		self.result = None

		# Of course, the caller may want to skip displaying the 
		# dialog altogether or display a different one. So, we
		# tell it how may differences there are.
		return self.diffcount

	# This notes which of the entry boxes in the center column have been
	# modified and turns on the [Merge] button when they all have been.
	def entry_output_changed_cb(self, widget, i):
		#print "entry changed:", widget, i
		self.changed.add(i)
		#print self.changed, len(self.changed), self.diffcount
		self.merge_button.set_sensitive(len(self.changed) == self.diffcount)

	# Intercept run()
	def run(self):
		self.merge_button.set_sensitive(len(self.changed) == self.diffcount)
		self.result = gtk.Dialog.run(self)
		return self.result

	# Get the merged row from the center column
	def get_output(self):
		# If there were differences to resolve and the user did so and pressed [Merge]
		# or the were no differences and we didn't bother displaying the dialog,
		if (self.result is not None and self.result == 1) or (self.result is None and self.diffcount == 0):
			answer = []
			for i in range(len(self.output_entries)):
				if self.output_entries[i] is not None:
					answer.append(self.output_entries[i].get_text())
				else:
					answer.append(self.input1[i])
			return answer
		else:
			return None

if __name__ == "__main__":
	dialog = MergeDialog(
		title="Merger Test",
		field_labels=['a', 'b', 'c', 'd', 'e'],
		show_all=True,
		)

	print "Test 1"
	diffcount = dialog.load(
		['1', '2', '3', '4', '5'],
		['one', 'two', 'three', '4', 'five'],
		suggestions={0: 'uno', 2:'quatro', 3:'synco', 4:'sece', 5:'sinto'}
		)
	print "%d differences to be resolved" % diffcount
	print dialog.run()
	dialog.hide()
	print "resolution:", dialog.get_output()

	print "Test 2"
	diffcount = dialog.load(
		['1', '2', '3', '4', '5'],
		['1', '2', '3', '4', '5'],
		)
	print "%d differences to be resolved" % diffcount
	print dialog.run()
	dialog.hide()
	print "resolution:", dialog.get_output()

	print "Test 3"
	dialog.show_all = False
	diffcount = dialog.load(
		['1', '2', '3', '4', '5'],
		['1', 'two', '3', '4', '5'],
		)
	print "%d differences to be resolved" % diffcount
	print dialog.run()
	dialog.hide()
	print "resolution:", dialog.get_output()

