#
# Required packages:
# * mingw32
# * librsvg2-bin
# * icoutils

CC=i586-mingw32msvc-gcc
WINDRES=i586-mingw32msvc-windres

gpx-trip-planner.exe: launcher.o resource.o
	$(CC) -o $@ $^

launcher.o: launcher.c
	$(CC) -c launcher.c

resource.o: resource.rc app_icon.ico
	$(WINDRES) -O coff -o resource.o resource.rc

app_icon.ico: app_icon.svg
	for size in 16 22 32 48 64 128; \
		do \
		rsvg -h $$size  -w $$size  app_icon.svg app_icon-$${size}x$${size}.png; \
		done
	icotool -c -o app_icon.ico app_icon-??x??.png

install: gpx-trip-planner.exe
	cp $^ ../../Code/launchers/
	cp $^ ../..

clean:
	rm -f *.o *.png *.ico *.exe

