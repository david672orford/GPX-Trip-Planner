# pykarta/draw/__init__.py
# Copyright 2013, Trinity College
# Last modified: 24 April 2013

import cairo
import math

# Add a rectangle with rounded corners to the path.
def rounded_rectangle(cr, x, y, w, h, r=20):
    # This is just one of the samples from 
    # http://www.cairographics.org/cookbook/roundedrectangles/
    #   A****BQ
    #  H      C
    #  *      *
    #  G      D
    #   F****E

    cr.move_to(x+r,y)                      # Move to A
    cr.line_to(x+w-r,y)                    # Straight line to B
    cr.curve_to(x+w,y,x+w,y,x+w,y+r)       # Curve to C, Control points are both at Q
    cr.line_to(x+w,y+h-r)                  # Move to D
    cr.curve_to(x+w,y+h,x+w,y+h,x+w-r,y+h) # Curve to E
    cr.line_to(x+r,y+h)                    # Line to F
    cr.curve_to(x,y+h,x,y+h,x,y+h-r)       # Curve to G
    cr.line_to(x,y+r)                      # Line to H
    cr.curve_to(x,y,x,y,x+r,y)             # Curve to A

# Add a string of line segements to the path.
def line_string(ctx, points):
	if len(points) < 1:		# empty route?
		return
	point = points[0]
	ctx.move_to(point[0], point[1])
	#for point in points[1:]:
	#	ctx.line_to(point[0], point[1])
	line_to = ctx.line_to
	map(lambda p: line_to(p[0], p[1]), points)

# Add a simple polygon to the path.
def polygon(ctx, points):
	line_string(ctx, points)
	ctx.close_path()

# Add arrow heads to show direction of travel.
# We work backwards from the end so as to have the best
# change of placing an arrowhead at or near the end of 
# the line. This looks better.
def line_string_arrows(ctx, points):
	arrow_min_interval = 50
	arrow_running_distance = arrow_min_interval
	# Note that if the len(points) is < 2 there will be no iterations. This is good.
	for i in reversed(range(len(points)-1)):
		p1 = points[i]
		p2 = points[i+1]
		width = p2[0] - p1[0]
		height = p2[1] - p1[1]
		distance = math.sqrt(width*width + height*height)
		arrow_running_distance += distance
		if arrow_running_distance > arrow_min_interval and distance > 20:
			barb1, barb2 = arrowhead_barbs(p1, p2, 10, 15)
			ctx.move_to(*barb1)
			ctx.line_to(*p2)
			ctx.line_to(*barb2)
			arrow_running_distance = 0
	
# Add a line with arrows showing direction to the path.
def route(ctx, points):
	line_string(ctx, points)
	line_string_arrows(ctx, points)

# Compute positions of the barb points of an arrow drawn at the end 
# of a line.
# See: http://kapo-cpp.blogspot.com/2008/10/drawing-arrows-with-cairo.html
def arrowhead_barbs(start_point, end_point, arrow_length, arrow_angle_degrees):
	start_x, start_y = start_point	
	end_x, end_y = end_point
	arrow_angle = math.radians(arrow_angle_degrees)
	angle = math.atan2(end_y - start_y, end_x - start_x) + math.pi
	x1 = end_x + arrow_length * math.cos(angle - arrow_angle)
	y1 = end_y + arrow_length * math.sin(angle - arrow_angle)
	x2 = end_x + arrow_length * math.cos(angle + arrow_angle)
	y2 = end_y + arrow_length * math.sin(angle + arrow_angle)
	return [[x1, y1], [x2, y2]]

def fill_with_style(ctx, style):
	fill_color = style.get("fill-color", (1.0, 1.0, 1.0, 0.5))
	if fill_color is not None:
		ctx.set_source_rgba(*fill_color)
		ctx.fill_preserve()

def stroke_with_style(ctx, style):
	stroke_color = style.get("color", (0.0, 0.0, 0.0, 1.0))
	dash_pattern = style.get("dash-pattern", ())
	width = style.get("width", 1)
	ctx.set_source_rgba(*stroke_color)
	ctx.set_dash(dash_pattern)
	ctx.set_line_width(width)
	ctx.stroke()

# Draw circles to represent the nodes of a geometric shape. Examples of
# such nodes would be route points or a polygon vertexes.
def node_dots(ctx, points, style={}):
	diameter = style.get("diameter", 7.0)
	stroke_color = style.get("border-color", (0.0, 0.0, 0.0, 1.0))
	fill_color = style.get("fill-color", (1.0, 1.0, 1.0, 1.0))

	for x, y in points:
		ctx.new_path()
		ctx.arc(x, y, diameter/2.0, 0, 2*math.pi)

		ctx.set_line_width(1.5)
		ctx.set_source_rgba(*stroke_color)
		ctx.stroke_preserve()

		ctx.set_source_rgba(*fill_color)
		ctx.fill()

def node_pluses(ctx, points, style={}):
	radius = style.get("diameter", 10) / 2.0
	underline_color = style.get("underline_color", (0.0, 0.0, 0.0, 1.0))	#(0.8, 0.2, 0.2, 1.0))
	color = style.get("color", (1.0, 1.0, 1.0, 1.0))
	line_width = style.get("line-width", 1)
	ctx.new_path()
	for x, y in points:
		ctx.move_to(x-radius, y)
		ctx.line_to(x+radius, y)
		ctx.move_to(x, y-radius)
		ctx.line_to(x, y+radius)
	ctx.set_line_cap(cairo.LINE_CAP_ROUND)
	ctx.set_line_width(4.0)
	ctx.set_source_rgba(*underline_color)
	ctx.stroke_preserve()
	ctx.set_line_width(2.0)
	ctx.set_source_rgba(*color)
	ctx.stroke()

# Place a label centered on the indicated point and just big
# enough to contain the indicated text. Stroke and fill.
def centered_label(ctx, x, y, text, fontsize=12):
	padding = fontsize / 4

	# Font
	ctx.select_font_face("sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
	ctx.set_font_size(fontsize)

	# Text dimensions
	# See http://www.cairographics.org/manual/cairo-cairo-scaled-font-t.html#cairo-text-extents-t
	extents = ctx.text_extents(text)
	#print "Extents of \"%s\":" % text, extents
	xbearing, ybearing, width, height, xadvance, yadvance = extents

	bubble_width = width + 2*padding
	bubble_height = height + 2*padding
	x -= bubble_width / 2
	y -= bubble_height / 2
	text_x = x + padding - xbearing
	text_y = y - ybearing + padding

	ctx.new_path()

	# Word bubble
	rounded_rectangle(ctx,
		x, y,
		bubble_width, bubble_height,
		5		# <-- corner radius
		)
	ctx.set_line_width(1)
	ctx.set_dash(())
	ctx.set_source_rgb(0.0, 0.0, 0.0)
	ctx.stroke_preserve()
	ctx.set_source_rgb(1.0, 1.0, 1.0)
	ctx.fill()

	# Word
	ctx.move_to(text_x, text_y)
	ctx.set_source_rgb(0.0, 0.0, 0.0)
	ctx.show_text(text)

# Print a label to the upper right of a POI marker. The x coordinate passed
# should be far enough to the right of the symbol so that the label does not
# overlap it. Stroke and fill.
def poi_label(ctx, x, y, text, fontsize=8, padding=1):
	# Font
	ctx.select_font_face("sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
	ctx.set_font_size(fontsize)

	extents = ctx.text_extents(text)
	#print "Extents of \"%s\":" % text, extents
	xbearing, ybearing, width, height, xadvance, yadvance = extents

	ctx.rectangle(x, y + ybearing - 2*padding, width + 2*padding, height + 2*padding)
	ctx.set_source_rgb(1.0, 1.0, 1.0)
	ctx.fill()

	ctx.move_to(x + padding - xbearing, y - padding)
	ctx.set_source_rgb(0.0, 0.0, 0.0)
	ctx.show_text(text)

	# The above sometimes leaves junk in the path
	ctx.new_path()

# Draw a red X with its center at the indicated point. Stroke.
def x_marks_the_spot(ctx, x, y, radius):
	ctx.move_to(x - radius, y - radius)
	ctx.line_to(x + radius, y + radius)
	ctx.move_to(x + radius, y - radius)
	ctx.line_to(x - radius, y + radius)
	ctx.set_line_cap(cairo.LINE_CAP_ROUND)
	ctx.set_line_width(10)
	ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
	ctx.stroke_preserve()
	ctx.set_line_width(5)
	#ctx.set_source_rgba(0.0, 0.7, 0.7, 1.0)	# interesting color
	ctx.set_source_rgba(0.8, 0.3, 0.3, 1.0)
	ctx.stroke()

