![logo](https://github.com/MaurizioB/jack_switch/raw/master/jack_switch.png) Jack Switch
===========

A simple insert switcher for jack clients  

If you need to easily switch outputs of your jack program (e.g. testing
equalization or compression against raw output, different output device or
reverb type, ...), then jack_switch might be helpful.  

jack_switch can be used for both stereo and mono audio interfaces, has a tray
icon enabled by default (that can be disabled via command line) and supports a
simple global keyboard shortcut interface.  
Once activated it shows the available outputs, that can be also enabled or
disabled using numbers on your keyboard. Use "x" to toggle the exclusive mode.  
If the keyboard shortcut interface is enabled (by using *-k* switch) the
default behaviour uses \<Win\>channel, where *\<Win\>* is the "Windows" key and
*channel* is the channel number, starting from 1. You can use alternate
keyboard modifiers (*\<Ctrl\>*, *\<Alt\>*, ...) combinations using the
*--modifiers* switch, just be careful for already assigned shortcuts - an alert on
the terminal will alert you.  

Keep in mind that this is a simple tool, still in development; it is intended
for simple "on the go" tests, and cannot be used for high-end projects. I will
try to add a buffer support to avoid sync problems, anyway.  

jack_switch is distributed **WITHOUT ANY WARRANTY**, it's just a script I made up
because I needed it, and I thought it might be useful to other users like you.
For any issues you can contact me at maurizio.berti on gmail, just keep in mind
that I'm no programmer, I just code for fun. Enjoy!


Requirements:
-------------

- pygtk2, keybinding
- [pyjack](https://pypi.python.org/pypi/py-jack/)
- numpy

Usage:
------

    jack_switch.py [-h] [-o n] [-m] [-x] [-k] [--modifiers \<Mod1\>\<Mod2\>\<...\>] [-f] [-q]

Without any argument, jack_switch will start with stereo inputs and 2 stereo outputs  

optional arguments:  

-o n, --outputs n (default and minimum: 2)  
Number of outputs (output pairs for stereo); maximum is 10 for stereo, 20 for mono  

-m, --mono  
Set mono inputs and outputs, if not specified jack_switch will create stereo input and outputs  

-x, --no-exclusive  
Disable exclusive mode on startup, can be overrided from the GUI  

-k, --keyboard  
Enable global keyboard shortcut support (default uses modifier+n, where *modifier* is the 'Win' key and *n* is the output number, starting from 1)  

--modifiers "\<Mod1\>\<Mod2\>\<...\>"  
Keyboard modifiers (\<Super\> - aka *Windows key*, \<Ctrl\>, \<Alt\>, ...). Implies *-k*  

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

--nostatusbar  
Disable sync errors status bar  

-q, --quiet  
Don't show sync errors in terminal  
