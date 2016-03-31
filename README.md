GPX Trip Planner is a viewer and editor for GPX files. It uses the Pykarta
map library written by the same author.

Install PyGTK+, Cairo, and RSVG:

    $ sudo apt-get install python-gtk2 python-cairo python-rsvg

Check out GPX Trip Planner and supporting libraries:

    $ mkdir GPX_Trip_Planner
    $ cd GPX_Trip_Planner
    $ mkdir pygtk
    $ cd pygtk
    $ git clone https://github.com/david672orford/pykarta.git
    $ git clone https://github.com/david672orford/pyapp.git
    $ cd ..
    $ git clone https://github.com/david672orford/GPX_Trip_Planner.git

Start:
    $ ./GPX_Trip_Planner/gpx-trip-planner

