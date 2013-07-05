# utils_gtk_radio.py
# Copyright 2013, Trinity College Computing Center
# Last modified: 11 January 2013

import gtk

# Create a set of radio buttons and pack them into the provided container.
class RadioChoices(object):
	def __init__(self, vbox, choices):
		self.choice_buttons = []
		group = None
		for choice_key, choice_label in choices:
			button = gtk.RadioButton(label=choice_label, group=group)
			vbox.pack_start(button)
			self.choice_buttons.append([button, choice_key])
			if group is None:
				group = button

	def get_choice_key(self):
		for choice_button, choice_key in self.choice_buttons:
			if choice_button.get_active():
				return choice_key
		raise Exception
	
