![logo](https://github.com/MaurizioB/jack_switch/raw/master/jack_switch.png) jack_switch
===========

A simple insert switcher for jack clients  

If you need to easily switch outputs of your jack program (e.g. testing equalization or compression against raw output, different output device or reverb type, ...), then jack_switch might be helpful.  

jack_switch is distributed WITHOUT ANY WARRANTY, it's just a script I made up because I needed it, and I thought it might be useful to other users like you. For any issues you can contact me at maurizio.berti on gmail, just keep in mind that I'm no programmer, I just code for fun. Enjoy!


Requirements:
-------------

- pygtk2, keybinding
- [pyjack](https://pypi.python.org/pypi/py-jack/)
- numpy

Usage:
------

    jack_switch.py [-h] [-o OUTPUTS] [-m] [-x] [-k] [--modifiers MODIFIERS] [-f] [-q]

Without any argument, jack_switch will start with stereo inputs and 2 stereo outputs  

optional arguments:  

-o, --outputs OUTPUTS (default, minimum: 2)  
Number of outputs (output pairs for stereo); maximum is 10 for stereo, 20 for mono  

-m, --mono  
Set mono inputs and outputs, if not specified jack_switch will create stereo input and outputs  

-x, --no-exclusive  
Disable exclusive mode on startup, can be overrided from the GUI  

-k, --keyboard  
Enable global keyboard shortcut support (default uses modifier+n, where *modifier* is the 'Win' key and *n* is the output number, starting from 1)  

--modifiers "MODIFIERS"  
Keyboard modifiers (<Super> - aka *Windows key*, <Ctrl>, <Alt>, ...). Implies *-k*  

-f, --func-keys  
Use F keys instead of numbers for global keyboard shortcut support. Implies *-k*  

-t, --hidetotray  
Start hidden to system tray  

--notray  
Disable tray support (mutually exclusive with *-t*)  

--noesc  
Disable close (or quit, if tray is disabled) on Escape key  

--escclose  
Always close on Escape key (mutually exclusive with *--noesc*  

-q, --quiet  
Don't show sync errors in terminal  
