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
    parser.add_argument('-x', '--no-exclusive', dest='exclusive', help='unset exclusive mode', action='store_false')
    parser.add_argument('-k', '--keyboard', dest='keybinding', help='enable global keyboard shortcut support', action='store_false', default=False)
    parser.add_argument('--modifiers', help='keyboard modifiers (<Super>, <Ctrl>, <Alt>, ...)')
    parser.add_argument('-f', '--func-keys', dest='funkey', help='use F keys instead of numbers', action='store_true', default=False)
    parser.add_argument('-q', '--quiet', help='don\'t show sync errors', action='store_true')
    return parser.parse_args()

args = cmdline()

if not args.exclusive:
    exclusive = False
else:
    exclusive = True

if args.keybinding and keybinding:
    #keybinder.init()
    keybinding = True
else:
    keybinding = False

if keybinding:
    if not args.modifiers:
        modifiers = '<Super>'
    else:
        modifiers = args.modifiers
else:
    modifiers = None

if args.funkey:
    funkey = 'F'
else:
    funkey = ''

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

try:
    jack.connect('sblive:capture_9', 'Switcher:input_l')
    jack.connect('sblive:capture_10', 'Switcher:input_r')
    jack.connect('Switcher:output_l', 'jm-sblive:sblive L')
    jack.connect('Switcher:output_r', 'jm-sblive:sblive R')
    jack.connect('Switcher:output2_l', 'jm-sblive:aux L')
    jack.connect('Switcher:output2_r', 'jm-sblive:aux R')
    jack.disconnect('sblive:capture_9', 'jm-sblive:sblive L')
    jack.disconnect('sblive:capture_10', 'jm-sblive:sblive R')
except:
    pass

class Processor:
    def __init__(self):
        self.input_stream = input_stream
        self.window = gtk.Window()
        self.window.set_title('Jack Switcher')
        self.window.connect('delete-event', self.quit)
        self.window.connect('key-press-event', self.keypress)
        hbox = gtk.HBox()
        sep = gtk.VSeparator()
        setter = gtk.CheckButton(label='Exclusive')
        self.exclusive = exclusive
        setter.set_active(self.exclusive)
        hbox.pack_end(setter, True, True, 10)
        hbox.pack_end(sep, True, True, 5)

        vbox = gtk.VBox()
        first = gtk.CheckButton(label='output 1')
        first.set_active(True)
        vbox.pack_start(first, True, True, 0)
        self.group = [first]
        setter.connect('toggled', self.toggle_exclusive)
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

        self.window.add(hbox)

        self.window.show_all()
        self.errors = [0, 0]

        self.jack_loop = gobject.idle_add(self.process_multi)
        self.keybinder()

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

    def process_multi(self):
        try:
            jack.process(numpy.concatenate(tuple(empty_stream if not self.output_ports[i] else input_stream for i in range(output_n))), input_stream)
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
        elif event.keyval == gtk.keysyms.Escape:
            self.quit()

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
