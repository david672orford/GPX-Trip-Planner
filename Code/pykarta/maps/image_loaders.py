# pykarta/maps/image_loaders.py
# Last modified: 5 April 2013

import gtk
import cairo

## From diogodivision's "BlingSwitcher"
#def pixbuf_from_surface(surface):
#	sio = StringIO.StringIO()
#	surface.write_to_png(sio)
#	sio.seek(0)
#	loader = gtk.gdk.PixbufLoader()
#	loader.write(sio.getvalue())
#	loader.close()
#	return loader.get_pixbuf()

def surface_from_pixbuf(pixbuf):
	surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, pixbuf.get_width(), pixbuf.get_height())
	ctx = cairo.Context(surface)
	gtk.gdk.CairoContext(ctx).set_source_pixbuf(pixbuf, 0, 0)
	ctx.paint()
	return surface

def surface_from_file(filename):
	# Disabled because resulting surfaces are slow.
	#if and filename.endswith(".png"):
	#	return cairo.ImageSurface.create_from_png(filename)

	pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
	return surface_from_pixbuf(pixbuf)

def surface_from_file_data(data):
	loader = gtk.gdk.PixbufLoader()
	loader.write(data)
	loader.close()
	return surface_from_pixbuf(loader.get_pixbuf())

