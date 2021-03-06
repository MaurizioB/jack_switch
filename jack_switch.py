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

import argparse, sys, re
from time import time as time

import gtk, gobject
import numpy, jack

try:
    import keybinder
    keybinding = True
except ImportError:
    keybinding = False

client_name = 'Switcher'

def cmdline(*args):
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--outports', metavar='n', type=int, help='number of outputs; default: 2 (maximum: 10 for stereo, 20 for mono)', default=2)
    parser.add_argument('-m', '--mono', help='set mono inputs and outputs', action='store_true')
    parser.add_argument('-I', '--input', metavar='client:port[*]', help='jack port[s] to try to auto connect to its inputs on startup')
    parser.add_argument('-O', '--output', metavar='client:port[*]', help='jack port[s] to try to auto connect to its outputs on startup')
    parser.add_argument('-x', '--no-exclusive', dest='exclusive', help='disable exclusive mode on startup', action='store_false')
    parser.add_argument('-k', '--keyboard', dest='keybinding', help='enable global keyboard shortcut support', action='store_true', default=False)
    parser.add_argument('--modifiers', metavar='"<Mod1><Mod2><...>"', help='keyboard modifiers (<Super>, <Ctrl>, <Alt>, ...), remember to use quotes; implies -k')
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

exclusive = args.exclusive

if args.keybinding:
    if not args.modifiers:
        modifiers = '<Super>'
    else:
        modifiers = args.modifiers
    args.keybinding = True
else:
    modifiers = ''

if args.funkey:
    funkey = 'F'
    args.keybinding = True
else:
    funkey = ''

keybinding = args.keybinding and keybinding

channels = 1 if args.mono else 2

if args.outports < 2:
    output_n = 2
    print 'Minimum output port number is 2'
elif args.outports > 10:
    if channels == 2:
        output_n = 10
        print 'Sorry, 20 outputs is the maximum output port number'
    elif args.outports > 20:
        output_n = 20
        print 'Sorry, 20 outputs is the maximum output port number'
else:
    output_n = args.outports

output_ports = [True] + [False]*(output_n-1) if output_n>0 else []
active = 0

jack.attach(client_name)
buf_size = jack.get_buffer_size()
#sam_size = float(jack.get_sample_rate())
#capture = numpy.zeros((2,int(sam_size)), 'f')

input_stream = numpy.zeros((channels, buf_size), 'f')
empty_stream = numpy.zeros((channels, buf_size), 'f')
#output_stream = numpy.zeros((4, buf_size), 'f')
#input_buffer = numpy.zeros((2, buf_size), 'f')

input_ports = []
if channels == 2:
    jack.register_port('input L', jack.IsInput)
    input_ports.append(client_name + ':' + 'input L')
    jack.register_port('input R', jack.IsInput)
    input_ports.append(client_name + ':' + 'input R')
else:
    input_ports.append(jack.register_port('input', jack.IsInput))


for i in range(output_n):
    if channels == 2:
        jack.register_port('output {} L'.format(i+1), jack.IsOutput)
        jack.register_port('output {} R'.format(i+1), jack.IsOutput)
    else:
        jack.register_port('output {}'.format(i+1), jack.IsOutput)

jack.activate()

if args.input:
    if ',' in args.input:
        capture_ports = args.input.split(',')
    else:
        jack_capture_ports = [p for p in jack.get_ports() if jack.get_port_flags(p) & jack.IsOutput]
        try:
            request = re.compile(args.input)
            capture_ports = [s.string for i in jack_capture_ports for s in [re.match(request, i)] if s]
        except:
            print 'input ports not valid'
    i = 0
    for p in capture_ports:
        try:
            print 'connect {} to {}'.format(p, input_ports[i])
            jack.connect(p, input_ports[i])
            i += 1
            if i >= len(input_ports):
                i = 0
        except Exception as err:
            print err
            print 'failed to connect: (\'{}\', \'{}\')'.format(p, input_ports[i])
            break

startup = time()

class Processor:
    def __init__(self):
        self.input_stream = input_stream
        self.output_ports = output_ports
        self.output_n = output_n

        self.window = gtk.Window()
        self.window.set_title('Jack Switcher')
        self.window.set_resizable(False)
        self.window.connect('delete-event', self.quit)
        self.window.connect('key-press-event', self.keypress)
        self.window.set_icon_from_file('jack_switch.png')
        self.mainbox = gtk.VBox()
        self.mainbox.set_border_width(1)

        toolbox = gtk.VBox()
        self.setter = gtk.CheckButton(label='E_xclusive')
        self.setter.set_can_focus(False)
        self.setter.connect('realize', self.restyle)
        #TODO valuta se si può togliere il valore di self.exclusive o gestirlo meglio
        self.exclusive = exclusive
        self.setter.set_active(self.exclusive)
        toolbox.pack_start(self.setter, False, False, 0)

        #TODO add cmdline support for fullmute
        self.fullmute = gtk.CheckButton(label='Allow _full mute')
        self.fullmute.set_can_focus(False)
        toolbox.pack_start(self.fullmute, False, False, 0)

        btns = gtk.HBox(True)
        self.full_btn = gtk.Button('All')
        self.full_btn.set_can_focus(False)
        self.full_btn.connect('clicked', self.activate_all, True)
        self.full_btn.set_sensitive(not self.exclusive)
        self.none_btn = gtk.Button('None')
        self.none_btn.set_can_focus(False)
        self.none_btn.connect('clicked', self.activate_all, False)
        self.none_btn.set_sensitive(self.fullmute.get_active())
        btns.pack_start(self.full_btn, True, True, 0)
        btns.pack_start(self.none_btn, True, True, 0)
        toolbox.pack_start(btns, False, False, 0)

        btns = gtk.HBox(True)
        add_btn = gtk.Button('+')
        add_btn.set_can_focus(False)
        add_btn.connect('clicked', self.add_ports)
        del_btn = gtk.Button('-')
        del_btn.set_can_focus(False)
        del_btn.connect('clicked', self.del_ports)
        btns.pack_start(add_btn, True, True, 0)
        btns.pack_start(del_btn, True, True, 0)
        toolbox.pack_start(btns, False, False, 0)

        self.outport_box = gtk.VBox()
        self.group = []
        self.setter.connect('toggled', self.toggle_exclusive)
        self.fullmute.connect('toggled', self.toggle_fullmute)

        for o in range(self.output_n):
            item = gtk.CheckButton(label='output {}'.format(o+1))
            self.outport_box.pack_start(item, False, False, 0)
            self.group.append(item)
            item.connect('toggled', self.selector, o)
            #item.connect('focus-in-event', self.grabbed)
        self.outport_box.get_children()[0].set_active(True)

        hbox = gtk.HBox()
        hbox.pack_start(self.outport_box, True, True, 10)
        sep = gtk.VSeparator()
        hbox.pack_start(sep, True, True, 5)
        hbox.pack_start(toolbox, True, True, 10)

        self.active = active

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

        self.jack_loop = gobject.idle_add(self.process_multi, priority=gobject.PRIORITY_DEFAULT_IDLE+10)
        self.keybindings = {}
        self.keybinder()

    def restyle(self, widget):
        style = widget.get_style().copy()
        style.bg[gtk.STATE_PRELIGHT] = style.bg[gtk.STATE_NORMAL]
        widget.set_style(style)


    def process_multi(self):
        try:
            jack.process(numpy.concatenate(tuple(empty_stream if not self.output_ports[i] else input_stream for i in range(self.output_n))), input_stream)
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
            noneselected = [item for item in self.group if item.get_active()]
            if not noneselected and self.exclusive and not self.fullmute.get_active():
                widget.set_active(True)
                return
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
            self.fullmute.set_sensitive(False)
            self.full_btn.set_sensitive(True)
            self.none_btn.set_sensitive(True)
            self.exclusive = False
        else:
            self.fullmute.set_sensitive(True)
            self.full_btn.set_sensitive(False)
            self.none_btn.set_sensitive(self.fullmute.get_active())
            self.exclusive = True
            for i, item in enumerate(self.group):
                if i != self.active:
                    item.set_active(False)
                else:
                    item.set_active(True)

    def toggle_fullmute(self, widget):
        #TODO verifica che ci siano output attivi
        if widget.get_active():
            self.none_btn.set_sensitive(True)
        else:
            self.group[self.active].set_active(True)
            self.none_btn.set_sensitive(False)

    def keypress(self, widget, event, fake=False):
        if fake or event.string.isdigit():
            if not fake:
                val = int(event.string)
            else:
                val = fake
            if val == 0:
                val = 10
            try:
                if self.exclusive and not self.fullmute.get_active():
                    self.group[val-1].set_active(True)
                else:
                    self.group[val-1].set_active(not self.group[val-1].get_active())
            except:
                return
            #self.selector(self.group[val-1], val-1)

        elif event.keyval == gtk.keysyms.Up:
            if not self.exclusive:
                if self.group[0].is_focus():
                    self.group[-1].grab_focus()
                    return True
                return False
            self.active = self.active - 1
            self.group[self.active].set_active(True)
            self.group[self.active].grab_focus()
            return True
        elif event.keyval == gtk.keysyms.Down:
            if not self.exclusive:
                if self.group[-1].is_focus():
                    self.group[0].grab_focus()
                    return True
                return False
            self.active = self.active + 1
            if self.active == self.output_n:
                self.active = 0
            #if self.active+1 == self.output_n:
                #self.active = -1
            #self.group[self.active+1].set_active(True)
            self.group[self.active].set_active(True)
            self.group[self.active].grab_focus()
            return True
        elif event.keyval == gtk.keysyms.x:
            self.setter.set_active(not self.setter.get_active())
        elif event.keyval == gtk.keysyms.f:
            self.fullmute.set_active(not self.fullmute.get_active())
        elif event.keyval == gtk.keysyms.a and not self.exclusive:
            self.activate_all(None, True)
        elif event.keyval == gtk.keysyms.n and (self.fullmute.get_active() or not self.exclusive):
            self.activate_all(None, False)
        elif event.keyval == gtk.keysyms.plus:
            self.add_ports()
        elif event.keyval == gtk.keysyms.minus:
            self.del_ports()
        elif event.keyval == gtk.keysyms.Escape:
            if args.noesc:
                return
            if args.escclose:
                self.quit()
            if args.notray:
                self.quit()
            self.window.hide()

    def bind(self, k):
        if not keybinding:
            return
        kb_output = keybinder.bind(modifiers+funkey+str(k), self.keypress, None, fake_key, k)
        if not kb_output:
            if modifiers: mod = '>+<'.join(modifiers.split('><'))+'+'
            else: mod = ''
            print 'Error! Check configuration or try custom key modifiers ("{}{}{}")'.format(mod, funkey, k)
        self.keybindings[k] = kb_output

    def unbind(self, k):
        if self.keybindings.get(k):
            try:
                keybinder.unbind(modifiers+funkey+str(k))
            except:
                pass

    def keybinder(self):
        if keybinding:
            for k in range(1, self.output_n+1):
                self.bind(k)
                #kb_output = keybinder.bind(modifiers+funkey+str(i+1), self.keypress, None, fake_key, i+1)
                #if not kb_output:
                    #if modifiers: mod = modifiers+'+'
                    #else: mod = ''
                    #if funkey: fk = funkey+'+'
                    #else: fk = ''
                    #print 'Error! Check configuration or try custom key modifiers ({}{}{})'.format(mod, fk, i+1)

    def activate_all(self, widget, selected):
        for item in self.group:
            item.set_active(selected)
        

    def add_ports(self, widget=None):
        if (self.output_n == 10 and channels == 2) or (self.output_n == 20):
            return
        self.output_n += 1
        item = gtk.CheckButton(label='output {}'.format(self.output_n))
        self.outport_box.pack_start(item, False, False, 0)
        item.show()
        self.group.append(item)
        self.output_ports.append(False)
        if channels == 2:
            jack.register_port('output {} L'.format(self.output_n), jack.IsOutput)
            jack.register_port('output {} R'.format(self.output_n), jack.IsOutput)
        else:
            jack.register_port('output {}'.format(self.output_n), jack.IsOutput)
        item.connect('toggled', self.selector, self.output_n-1)
        self.bind(self.output_n)

    def del_ports(self, widget=None):
        if self.output_n == 2:
            return
        lastport = self.group[-1]
        if lastport.is_focus():
            self.group[-2].grab_focus()
        self.outport_box.remove(lastport)
        if channels == 2:
            jack.unregister_port('output {} L'.format(self.output_n))
            jack.unregister_port('output {} R'.format(self.output_n))
        else:
            jack.unregister_port('output {}'.format(self.output_n))
        self.output_n -= 1
        self.group.pop()
        self.output_ports.pop()
        self.unbind(self.output_n)

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
            jack.process(numpy.concatenate(tuple(empty_stream if not i==self.active else input_stream for i in range(self.output_n))), input_stream)
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
    #fake keypress class for global keybinding
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

