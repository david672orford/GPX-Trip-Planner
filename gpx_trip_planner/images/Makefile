# This makefile builds PNG versions of the application icon and the GPX file icon.
# These are needed by the windowing systems and file managers.

all: app_icon.svg gpx-file.svg
	for size in 16 22 32 48 64 128 256; \
		do \
		rsvg-convert -w $$size -h $$size app_icon.svg -o app_icon-$${size}x$${size}.png; \
		rsvg-convert -w $$size -h $$size gpx-file.svg -o gpx-file-$${size}x$${size}.png; \
		done

clean:
	rm *.png

