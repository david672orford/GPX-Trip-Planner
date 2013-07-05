# utils_rsvg_ctypes.py
# Last modified: 20 March 2012

import sys
import ctypes

if sys.platform == 'win32':
	librsvg    = ctypes.CDLL('librsvg-2-2.dll')
	libgobject = ctypes.CDLL('libgobject-2.0-0.dll')
elif sys.platform == 'darwin':
	# Don't forget to set DYLD_FALLBACK_LIBRARY_PATH.
	librsvg    = ctypes.CDLL('librsvg-2.2.dylib')
	libgobject = ctypes.CDLL('libgobject-2.0.dylib')
else:
	raise Exception("No case for platform %s" % sys.platform)

libgobject.g_type_init()

# svg.Handle(filename)
class Handle():
	class RsvgDimensionData(ctypes.Structure):
		_fields_ = [("width", ctypes.c_int),
		            ("height", ctypes.c_int),
		            ("em", ctypes.c_double),
		            ("ex", ctypes.c_double)]

	class PycairoContext(ctypes.Structure):
		_fields_ = [("PyObject_HEAD", ctypes.c_byte * object.__basicsize__),
		            ("ctx", ctypes.c_void_p),
		            ("base", ctypes.c_void_p)]

	def __init__(self, path):
		self.path = path
		error = ''
		self.handle = librsvg.rsvg_handle_new_from_file(self.path, error)

	def get_dimension_data(self):
		svgDim = self.RsvgDimensionData()
		librsvg.rsvg_handle_get_dimensions(self.handle, ctypes.byref(svgDim))
		return (svgDim.width, svgDim.height)	# what about em and ex?

	def render_cairo(self, ctx):
		ctx.save()
		z = self.PycairoContext.from_address(id(ctx))
		librsvg.rsvg_handle_render_cairo(self.handle, z.ctx)
		ctx.restore()

	def get_pixbuf(self):
		capi = PyGObjectCPAI()
		pixbuf = librsvg.rsvg_handle_get_pixbuf(self.handle)
		return capi.pygobject_new(pixbuf)

# See: http://wiki.maemo.org/PyMaemo/Accessing_APIs_without_Python_bindings
# ctypes wrapper for pygobject_new(), based on code snippet from
# http://faq.pygtk.org/index.py?req=show&file=faq23.041.htp
class _PyGObject_Functions(ctypes.Structure):
    _fields_ = [
        ('register_class',
            ctypes.PYFUNCTYPE(ctypes.c_void_p, ctypes.c_char_p,
            ctypes.c_int, ctypes.py_object, ctypes.py_object)),
        ('register_wrapper',
            ctypes.PYFUNCTYPE(ctypes.c_void_p, ctypes.py_object)),
        ('register_sinkfunc',
            ctypes.PYFUNCTYPE(ctypes.py_object, ctypes.c_void_p)),
        ('lookupclass',
            ctypes.PYFUNCTYPE(ctypes.py_object, ctypes.c_int)),
        ('newgobj',
            ctypes.PYFUNCTYPE(ctypes.py_object, ctypes.c_void_p)),
    ]
 
class PyGObjectCPAI(object):
	def __init__(self):
		import gobject
		py_obj = ctypes.py_object(gobject._PyGObject_API)
		addr = ctypes.pythonapi.PyCObject_AsVoidPtr(py_obj)
		self._api = _PyGObject_Functions.from_address(addr)
 
	def pygobject_new(self, addr):
		return self._api.newgobj(addr)

