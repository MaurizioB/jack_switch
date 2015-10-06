jack_switch
===========

A simple switcher for jack clients  

If you need to easily switch outputs of your jack program (e.g. testing equalization or compression against raw output, different output device or reverb type, ...), then jack_switch might be helpful.  
jack_switch is distributed WITHOUT ANY WARRANTY, it's just a script I made up because I needed it, and I thought it might be useful to other users like you. For any issues you can contact me at maurizio.berti on gmail, just keep in mind that I'm no programmer, I just code for fun. Enjoy!
  
Requirements:
-------------

- pygtk2, keybinding
- pyjack (https://pypi.python.org/pypi/py-jack/)
- numpy

Usage:
------

jack_switch.py [-h] [-o OUTPUTS] [-m] [-x] [-k] [--modifiers MODIFIERS] [-f] [-q]

optional arguments:  

-o, --outputs OUTPUTS  
outputs; default: 2 (maximum: 10 for stereo, 20 for mono)  

-m, --mono  
set mono inputs and outputs  

-x, --no-exclusive  
unset exclusive mode  

-k, --keyboard  
enable global keyboard shortcut support  

-modifiers MODIFIERS  
keyboard modifiers (<Super>, <Ctrl>, <Alt>, ...)  

-f, --func-keys  
use F keys instead of numbers  

-q, --quiet  
don't show sync errors  
