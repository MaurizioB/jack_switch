#!/usr/bin/python
# -*- coding: utf-8 -*-
# jack_switch is a simple switcher for jack clients
# If you need to easily switch outputs of your jack program (e.g. testing
# equalization or compression against raw output, different output device or
# reverb type, ...), then jack_switch might be helpful.
# jack_switch is distributed WITHOUT ANY WARRANTY, it's just a script I made
# up because I needed it, and I thought it might be useful to other users like
# you. For any issues you can contact me at maurizio.berti on gmail, just keep
# in mind that I'm no programmer, I just code for fun. Enjoy!

import numpy, jack, argparse, sys
from time import time as time
import gtk, gobject
try:
    import keybinder
    keybinding = True
except:
    keybinding = False

client_name = 'Switcher'

def cmdline(*args):
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--outputs', type=int, help='outputs; default: 2 (maximum: 10 for stereo, 20 for mono)', default=2)
    parser.add_argument('-m', '--mono', help='set mono inputs and outputs', action='store_false')
    parser.add_argument('-x', '--no-exclusive', dest='exclusive', help='disable exclusive mode on startup', action='store_false')
    parser.add_argument('-k', '--keyboard', dest='keybinding', help='enable global keyboard shortcut support', action='store_false', default=False)
    parser.add_argument('--modifiers', help='keyboard modifiers (<Super>, <Ctrl>, <Alt>, ...), remember to use quotes; implies -k')
    parser.add_argument('-f', '--func-keys', dest='funkey', help='use F keys instead of numbers; implies -k', action='store_true', default=False)

    tray = parser.add_mutually_exclusive_group()
    tray.add_argument('-t', '--hidetotray', help='start hidden to system tray', action='store_true')
    tray.add_argument('--notray', help='disable tray support', action='store_true')

    escape = parser.add_mutually_exclusive_group()
    escape.add_argument('--noesc', help='disable close on Escape key', action='store_true')
    escape.add_argument('--escclose', help='always quit on Escape key', action='store_true')

    parser.add_argument('--nostatusbar', dest='statusbar', help='disable sync errors status bar', action='store_false', default=True)
    parser.add_argument('-q', '--quiet', help='don\'t show sync errors on terminal', action='store_true')
    return parser.parse_args()

args = cmdline()

if not args.exclusive:
    exclusive = False
else:
    exclusive = True

if keybinding:
    if not args.modifiers:
        modifiers = '<Super>'
    else:
        modifiers = args.modifiers
        args.keybinding = True
else:
    modifiers = None

if args.funkey:
    funkey = 'F'
    args.keybinding = True
else:
    funkey = ''

if args.keybinding and keybinding:
    #keybinder.init()
    keybinding = True
else:
    keybinding = False

if not args.mono:
    channels = 1
else:
    channels = 2

if args.outputs < 2:
    output_n = 2
elif args.outputs > 10:
    if channels == 2:
        output_n = 10
        print 'Sorry, 20 outputs is the maximum output port number'
    elif args.outputs > 20:
        output_n = 20
        print 'Sorry, 20 outputs is the maximum output port number'
else:
    output_n = args.outputs

output_ports = [True if i==0 else False for i in range(output_n)]
active = 0

jack.attach(client_name)
buf_size = jack.get_buffer_size()
#sam_size = float(jack.get_sample_rate())
#capture = numpy.zeros((2,int(sam_size)), 'f')

input_stream = numpy.zeros((channels, buf_size), 'f')
empty_stream = numpy.zeros((channels, buf_size), 'f')
#output_stream = numpy.zeros((4, buf_size), 'f')
#input_buffer = numpy.zeros((2, buf_size), 'f')

if channels == 2:
    jack.register_port('input L', jack.IsInput)
    jack.register_port('input R', jack.IsInput)
else:
    jack.register_port('input', jack.IsInput)


for i in range(output_n):
    if channels == 2:
        jack.register_port('output {} L'.format(i+1), jack.IsOutput)
        jack.register_port('output {} R'.format(i+1), jack.IsOutput)
    else:
        jack.register_port('output {}'.format(i+1), jack.IsOutput)

jack.activate()
startup = time()

class Processor:
    def __init__(self):
        self.input_stream = input_stream
        self.window = gtk.Window()
        self.window.set_title('Jack Switcher')
        self.window.set_resizable(False)
        self.window.connect('delete-event', self.quit)
        self.window.connect('key-press-event', self.keypress)
        self.window.set_icon_from_file('jack_switch.png')
        self.mainbox = gtk.VBox()
        self.mainbox.set_border_width(1)
        hbox = gtk.HBox()
        sep = gtk.VSeparator()
        self.setter = gtk.CheckButton(label='E_xclusive')
        self.exclusive = exclusive
        self.setter.set_active(self.exclusive)
        hbox.pack_end(self.setter, True, True, 10)
        hbox.pack_end(sep, True, True, 5)

        vbox = gtk.VBox()
        first = gtk.CheckButton(label='output 1')
        first.set_active(True)
        vbox.pack_start(first, True, True, 0)
        self.group = [first]
        self.setter.connect('toggled', self.toggle_exclusive)
        first.connect('toggled', self.selector, 0)

        for o in range(output_n-1):
            item = gtk.CheckButton(label='output {}'.format(o+2))
            vbox.pack_start(item, True, True, 0)
            self.group.append(item)

        for i, item in enumerate(self.group[1:]):
            item.connect('toggled', self.selector, i+1)

        hbox.pack_start(vbox, True, True, 10)

        self.active = active
        self.output_ports = output_ports

        self.mainbox.pack_start(hbox, True, True, 0)

        if args.statusbar:
            statusbar = gtk.HBox(spacing=2)
            #inframe = gtk.Frame()
            self.insync_lbl = gtk.Entry()
            self.insync_lbl.set_width_chars(5)
            self.insync_lbl.set_text('In: 0')
            self.insync_lbl.set_sensitive(False)
            #inframe.add(self.insync_lbl)

            #outframe = gtk.Frame()
            self.outsync_lbl = gtk.Entry()
            self.outsync_lbl.set_width_chars(5)
            self.outsync_lbl.set_sensitive(False)
            self.outsync_lbl.set_text('Out: 0')
            #outframe.add(self.outsync_lbl)

            #ratioframe = gtk.Frame()
            self.ratio_lbl = gtk.Entry()
            self.ratio_lbl.set_width_chars(8)
            self.ratio_lbl.set_sensitive(False)
            self.ratio_lbl.set_text('Ratio: 0')
            #ratioframe.add(self.ratio_lbl)

            statusbar.pack_start(self.insync_lbl, False, False, 1)
            statusbar.pack_start(self.outsync_lbl, False, False, 1)
            statusbar.pack_start(self.ratio_lbl, True, True, 1)

            self.mainbox.pack_start(statusbar, True, True, 2)
        self.window.add(self.mainbox)

        if not args.notray:
            self.icon = gtk.status_icon_new_from_file('jack_switch.png')
            self.icon.set_tooltip('Jack Switch')
            self.menu = gtk.Menu()
            self.togglewin_menuitem = gtk.MenuItem('')
            self.togglewin_menuitem.connect('activate', self.window_toggle)
            self.menu.append(self.togglewin_menuitem)
            quitter = gtk.ImageMenuItem(stock_id=gtk.STOCK_QUIT)
            quitter.connect('activate', self.quit)
            self.menu.append(quitter)
            self.menu.show_all()
            self.icon.connect('popup-menu', self.popup)
            self.icon.connect('activate', self.window_toggle)
        else:
            self.icon = None


        if not args.hidetotray:
            self.window.show_all()
        self.errors = [0, 0]

        self.jack_loop = gobject.idle_add(self.process_multi)
        self.keybinder()

    def process_multi(self):
        try:
            jack.process(numpy.concatenate(tuple(empty_stream if not self.output_ports[i] else input_stream for i in range(output_n))), input_stream)
        except jack.InputSyncError:
            self.errors[0] += 1
            if args.statusbar:
                self.status_update(0)
            if not args.quiet:
                sys.stdout.write('\r\x1b[K \033[1mInput: {}\033[0m\tOutput: {}\tRatio: {}'.format(self.errors[0], self.errors[1], self.error_ratio()))
                sys.stdout.flush()
        except jack.OutputSyncError:
            self.errors[1] += 1
            if args.statusbar:
                self.status_update(1)
            if not args.quiet:
                sys.stdout.write('\r\x1b[K Input: {}\t\033[1mOutput: {}\033[0m\tRatio: {}'.format(self.errors[0], self.errors[1], self.error_ratio()))
                sys.stdout.flush()
        return True

    def status_update(self, latest):
        if latest == 0:
            insync = 'In: {}'.format(self.errors[0])
            self.insync_lbl.set_width_chars(len(insync))
            self.insync_lbl.set_text(insync)
        else:
            outsync = 'Out: {}'.format(self.errors[1])
            self.outsync_lbl.set_width_chars(len(outsync))
            self.outsync_lbl.set_text(outsync)
        self.ratio_lbl.set_text(self.error_ratio())

    def error_ratio(self):
        tottime = time()-startup
        if tottime < 5:
            return '[processing]'
        return '{:.2f} every 5s'.format(sum(self.errors)*5/tottime)

    def selector(self, widget, selected):
        if not widget.get_active():
            self.output_ports[selected] = False
            return
        if self.exclusive:
            for i, item in enumerate(self.group):
                if i != selected:
                    item.set_active(False)
                else:
                    item.set_active(True)
        self.output_ports[selected] = True
        self.active = selected

    def toggle_exclusive(self, widget):
        if not widget.get_active():
            self.exclusive = False
        else:
            self.exclusive = True
            for i, item in enumerate(self.group):
                if i != self.active:
                    item.set_active(False)
                else:
                    item.set_active(True)

    def keypress(self, widget, event, fake=False):
        if fake or event.string.isdigit():
            if not fake:
                val = int(event.string)
            else:
                val = fake
            if val == 0:
                val = 10
            try:
                if self.exclusive:
                    self.group[val-1].set_active(True)
                else:
                    self.group[val-1].set_active(not self.group[val-1].get_active())
            except:
                return
            #self.selector(self.group[val-1], val-1)
        elif event.keyval == gtk.keysyms.x:
            self.setter.set_active(not self.setter.get_active())
        elif event.keyval == gtk.keysyms.Escape:
            if args.noesc:
                return
            if args.escclose:
                self.quit()
            if args.notray:
                self.quit()
            self.window.hide()

    def keybinder(self):
        if keybinding:
            for i in range(output_n):
                kb_output = keybinder.bind(modifiers+funkey+str(i+1), self.keypress, None, fake_key, i+1)
                if not kb_output:
                    print 'check configuration or try custom key modifiers'

    def test(self, output):
        print output

    def quit(self, *args):
        jack.deactivate()
        jack.detach()
        gtk.main_quit()
        print ''

    def window_toggle(self, status_icon):
        if self.window.get_visible():
            self.window.hide()
        else:
            self.window.show_all()

    def popup(self, status_icon, button, time):
        if self.window.get_visible():
            self.togglewin_menuitem.set_label('Hide')
        else:
            self.togglewin_menuitem.set_label('Show')
        self.menu.popup(None, None, None, button, time)



    def process(self):
        try:
            #array = tuple(empty_stream if not i==self.active else input_stream for i in range(output_n))
            jack.process(numpy.concatenate(tuple(empty_stream if not i==self.active else input_stream for i in range(output_n))), input_stream)
        except jack.InputSyncError:
            if not args.quiet:
                self.errors[0] += 1
                sys.stdout.write('\r\x1b[K \033[1mInput: {}\033[0m\tOutput: {}\tRatio: {}'.format(self.errors[0], self.errors[1], self.error_ratio()))
                sys.stdout.flush()
        except jack.OutputSyncError:
            if not args.quiet:
                self.errors[1] += 1
                sys.stdout.write('\r\x1b[K Input: {}\t\033[1mOutput: {}\033[0m\tRatio: {}'.format(self.errors[0], self.errors[1], self.error_ratio()))
                sys.stdout.flush()
        return True

class fake_key:
    string = ''
    keyval = ''
    def __init__(self):
        pass

if __name__ == '__main__':
    proc = Processor()
    gtk.main()

try:
    jack.deactivate()
    jack.detach()
except:
    pass

