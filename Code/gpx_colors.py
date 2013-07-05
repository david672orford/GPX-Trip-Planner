import gobject
import gtk

colors = [
	['Red',         (1.0, 0.0, 0.0, 1.0)],
	['DarkRed',     (0.5, 0.0, 0.0, 1.0)],
	['Green',       (0.0, 1.0, 0.0, 1.0)],
	['DarkGreen',   (0.0, 0.5, 0.0, 1.0)],
	['Blue',        (0.0, 0.0, 1.0, 1.0)],
	['DarkBlue',    (0.0, 0.0, 0.5, 1.0)],
	['Cyan',        (0.0, 1.0, 1.0, 1.0)],
	['DarkCyan',    (0.0, 0.5, 0.5, 1.0)],
	['Magenta',     (1.0, 0.0, 1.0, 1.0)],
	['DarkMagenta', (0.5, 0.0, 0.5, 1.0)],
	['Yellow',      (1.0, 1.0, 0.0, 1.0)],
	['DarkYellow',  (0.5, 0.5, 0.0, 1.0)],
	['Black',       (0.0, 0.0, 0.0, 1.0)],
	['DarkGray',    (0.5, 0.5, 0.5, 1.0)],
	['LightGray',   (0.8, 0.8, 0.8, 1.0)],
	['White',       (1.0, 1.0, 1.0, 1.0)],
	['Transparent', (0.0, 0.0, 0.0, 0.0)],
	]

rgb_by_name = {}
index_by_name = {}
liststore = gtk.ListStore(gobject.TYPE_STRING)
i = 0
for color in colors:
	rgb_by_name[color[0]] = color[1]
	index_by_name[color[0]] = i
	liststore.append([color[0]])
	i += 1

