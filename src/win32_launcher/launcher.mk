#
# Required packages:
# $ sudo apt-get install mingw-w64 librsvg2-bin icoutils

# Define this before including
#LAUNCHER_NAME=

#CC=i586-mingw32msvc-gcc
CC=i686-w64-mingw32-gcc
RSVG_CONVERT=rsvg-convert
ICOTOOL=icotool
#WINDRES=i586-mingw32msvc-windres
WINDRES=i686-w64-mingw32-windres

$(LAUNCHER_NAME): launcher.o resource.o
	$(CC) -o $@ $^

launcher.o: launcher.c
	$(CC) -I. -c $^

# Resource file documentation:
# * http://msdn.microsoft.com/en-us/library/aa381058.aspx
# Discussion of icon sizes:
# * http://stackoverflow.com/questions/3236115/which-icon-sizes-should-my-windows-applications-icon-include
resource.o: resource.rc app_icon.svg debug_console.svg
	for size in 16 32 48 256; \
		do \
		$(RSVG_CONVERT) -w $${size} -h $${size} app_icon.svg -o app_icon-$${size}x$${size}.png; \
		done; \
	$(ICOTOOL) -c -o app_icon.ico app_icon-*x*.png; \
	for size in 16 32 48; \
		do \
		$(RSVG_CONVERT) -w $${size} -h $${size} debug_console.svg -o debug_console-$${size}x$${size}.png; \
		done; \
	$(ICOTOOL) -c -o debug_console.ico debug_console-*x*.png; \
	$(WINDRES) -O coff -o resource.o resource.rc

install: $(LAUNCHER_NAME)
	cp $^ ../../Code/launchers/win32/
	cp $^ ../../

clean:
	rm -f *.o *.png *.ico *.exe

