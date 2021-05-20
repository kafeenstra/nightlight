# nightlight
my_night_light sets displays brightness and gamma to avoid strained eyes at nighttime. 

In particular, it sets the gamma more red and less blue (like Ubuntu's Night Light), but also less bright.

Without options, it sets values depending on the twilight periods relative to sunrise and sunset (as determined by Astral). It
is also possible to set (once) displays to a given value, or relative (up/down), or to request current settings value. Default settings are stored
in the config file.

When running automatically, if the update period is long(er) or at startup, it changes brightness levels gradually from the current value. 
This behaviour can also be requested when setting a specific value (or relative), by the -s (or --smooth) option.

The backand is a wrapper around the xrandr commandline tool. Ideally, one would want to use directly the python Xlib with randr extensions, 
but it is beyond me to figure out how that works for setting gamma and/or brightness. Closest I got was to get the gamma (red, green, blue)
from randr.get_crt_gamma, however how to manipulat this (1024) long array I don't know.

Some pointers:

See https://github.com/python-xlib/python-xlib/blob/master/Xlib/ext/randr.py

See https://stackoverflow.com/questions/8705814/get-display-count-and-resolution-for-each-display-in-python-without-xrandr
