# Trying to figure out how to control the height of a frame in grid mode.
#
# More specifically, in the application, I'm finding that when I replace an
# OptionMenu with an Entry and Clear button, there's a resizing blip in the UI.
# I'd like to figure out how to work around it.
#
# It appears the answer is to rowconfigure the minsize of each frame which
# contains UI elements. It also appears to be helpful to have a disabled Clear
# button be part of the frame, which can be enabled when the selection value
# has been fixed.
from Tkinter import *
from Tkinter import _setit

class ui(Frame):

    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.parent = parent
        # For frames that enclose UI elements.
        self.f = dict()
        # For selection widgets inside frames.
        self.w = dict()
        # For labels, if any.
        self.l = dict()
        # For wide Entry boxes.
        self.wide = dict()
        # For entry boxes, once a particular value has been selected.
        self.e = dict()
        # For clear buttons inside frames.
        self.r = dict()
        # For StringVars.
        self.v = dict()
        # For traces on StringVars.
        self.tv = dict()
        # For unique StringVar names.
        self.svi = 0

    def _uname(self, st):
        self.svi += 1
        return '%s_%d' % (st, self.svi)

    def add_option_menu(self, k, row):
        self.f[k] = Frame(self.parent, padx=5)
        f = self.f[k]
        self.v[k] = StringVar(f, name=self._uname(k))
        self.v[k].set('')
        self.w[k] = OptionMenu(f, self.v[k], self.v[k].get())
        self.e[k] = Entry(f, disabledforeground='blue',
            disabledbackground='#cdcdff')
        self.r[k] = Button(f, text='Clear', command=eval('self.clear_%s' % k))
        self.r[k].grid(row=0, column=1)
        self.set_option_choices(k)
        f.grid(row=row, column=0, columnspan=2, sticky='ew')
        f.columnconfigure(0, weight=1, minsize=270)
        f.columnconfigure(1, minsize=70)
        f.rowconfigure(0, minsize=35)

    def add_narrow_option_menu(self, k, row, column, label=''):
        self.f[k] = Frame(self.parent, padx=5)
        f = self.f[k]
        option_column = 0
        if label:
            self.l[k] = Label(f, text=label)
            self.l[k].grid(row=0, column=0, sticky='ew')
            option_column = 1
        self.v[k] = StringVar(f, name=self._uname(k))
        self.v[k].set('')
        self.w[k] = OptionMenu(f, self.v[k], self.v[k].get())
        self.e[k] = Entry(f, disabledforeground='blue',
            disabledbackground='#cdcdff', width=8)
        self.r[k] = Button(f, text='Clear', command=eval('self.clear_%s' % k))
        self.r[k].grid(row=0, column=1+option_column)
        self.set_option_choices(k, column=option_column)
        f.grid(row=row, column=column, sticky='ew')
        if label:
            f.columnconfigure(0, minsize=50)
        f.columnconfigure(option_column, weight=1, minsize=120)
        f.columnconfigure(1+option_column, minsize=70)
        f.rowconfigure(0, minsize=35)

    def add_entry_box(self, k, row, column, label=''):
        self.f[k] = Frame(self.parent, padx=5)
        f = self.f[k]
        self.l[k] = Label(f, text=label)
        self.l[k].grid(row=0, column=0, sticky='ew')
        self.w[k] = Entry(f, width=16)
        self.e[k] = Entry(f, disabledforeground='blue',
            disabledbackground='#cdcdff', width=16)
        self.r[k] = Button(f, text='Clear', command=eval('self.clear_%s' % k))
        self.r[k].grid(row=0, column=2)
        self.set_blank_entry(k)
        f.grid(row=row, column=column, sticky='ew')
        f.columnconfigure(0, minsize=50)
        f.columnconfigure(2, minsize=70)
        f.rowconfigure(0, minsize=35)
    
    def add_wide_entry_box(self, k, row, label=''):
        self.f[k] = Frame(self.parent, padx=5)
        self.wide[k] = True
        f = self.f[k]
        self.l[k] = Label(f, text=label)
        self.l[k].grid(row=0, column=0, sticky='ew')
        self.w[k] = Entry(f, width=8)
        self.e[k] = Entry(f, disabledforeground='blue',
            disabledbackground='#cdcdff', width=8)
        self.r[k] = Button(f, text='Clear', command=eval('self.clear_%s' % k))
        self.r[k].grid(row=1, column=1)
        self.set_blank_wide_entry(k)
        f.grid(row=row, column=0, columnspan=2, sticky='ew')
        f.columnconfigure(0, weight=1, minsize=270)
        f.columnconfigure(1, minsize=70)
        f.rowconfigure(0, minsize=10)
        f.rowconfigure(1, minsize=35)

    def clear_Make(self, *args):
        self.search_modified('Clear', 'Make', 0)

    def clear_Model(self, *args):
        self.search_modified('Clear', 'Model', 1)

    def clear_MinYear(self, *args):
        self.search_modified('Clear', 'MinYear', 3, 0)

    def clear_MaxYear(self, *args):
        self.search_modified('Clear', 'MaxYear', 3, 1)

    def clear_MinPrice(self, *args):
        self.search_modified('Clear', 'MinPrice', 2, 0)

    def clear_MaxPrice(self, *args):
        self.search_modified('Clear', 'MaxPrice', 2, 1)

    def clear_Keywords(self, *args):
        self.search_modified('Clear', 'Keywords', 4)

    def set_option_choices(self, k, column=0):
        print "-- Set option", k
        self.e[k].grid_remove()
        self.r[k].configure(state='disabled')
        if k.endswith('Year'):
            self.legal = ['%s %s' % (k[:3], k[3:])]
            for i1 in range(3):
                self.legal.append('%s' % (i1 + 2012))
        else:
            self.legal = ['Select %s' % k]
            for i1 in range(3):
                self.legal.append('%s %s' % (k, i1+1))
        self.v[k].set(self.legal[0])
        self.w[k]['menu'].delete(0, 'end')
        for choice in self.legal:
            self.w[k]['menu'].add_command(label=choice,
                command=_setit(self.v[k], choice))
        self.w[k].grid(row=0, column=column, sticky='ew')
        self.tv[k] = self.v[k].trace('w', self.search_modified)

    def set_blank_entry(self, k):
        self.e[k].grid_remove()
        self.r[k].configure(state='disabled')
        self.w[k].delete(0, 'end')
        self.w[k].grid(row=0, column=1, sticky='ew')
        self.w[k].bind('<Return>', self.search_modified)

    def set_blank_wide_entry(self, k):
        self.e[k].grid_remove()
        self.r[k].configure(state='disabled')
        self.w[k].delete(0, 'end')
        self.w[k].grid(row=1, column=0, sticky='ew')
        self.w[k].bind('<Return>', self.search_modified)

    def set_option_entry(self, k):
        print "-- Set option entry", k
        self.w[k].grid_remove()
        self.r[k].configure(state='normal')
        self.e[k].configure(state='normal')
        self.e[k].delete(0, 'end')
        self.e[k].insert(0, self.v[k].get())
        self.e[k].configure(state='disabled')
        column = 0
        if k in ['MinYear', 'MaxYear']:
            column = 1
        self.e[k].grid(row=0, column=column, sticky='ew')
        self.v[k].trace_vdelete('w', self.tv[k])

    def set_entry_entry(self, k, wtext):
        print "-- Set entry entry", k, wtext
        self.w[k].grid_remove()
        self.r[k].configure(state='normal')
        self.e[k].configure(state='normal')
        self.e[k].delete(0, 'end')
        self.e[k].insert(0, wtext)
        self.e[k].configure(state='disabled')
        self.e[k].grid(row=0, column=1, sticky='ew')

    def set_entry_wide_entry(self, k, wtext):
        print "-- Set entry wide entry", k, wtext
        self.w[k].grid_remove()
        self.r[k].configure(state='normal')
        self.e[k].configure(state='normal')
        self.e[k].delete(0, 'end')
        self.e[k].insert(0, wtext)
        self.e[k].configure(state='disabled')
        self.e[k].grid(row=1, column=0, sticky='ew')

    def search_modified(self, *args):
        # The modified OptionMenu is in args[0], but we've appended a nunber to
        # it. Get the key of the modified OptionMenu.
        cvar = args[0]
        print "-- In search_modified", args
        if isinstance(args[0], Event):
            # Ugh. Figure out which widget had the Event by comparing memory
            # locations.
            ewidget = args[0].widget
            k = filter(lambda k: self.w[k] == ewidget, self.w)[0]
            if k in self.wide:
                self.set_entry_wide_entry(k, ewidget.get())
            else:
                self.set_entry_entry(k, ewidget.get())
        elif cvar == 'Clear':
            k = args[1]
            print "-- Reset to", k
            if k in ['MinYear', 'MaxYear']:
                self.set_option_choices(k, 1)
            elif k in self.l:
                if k in self.wide:
                    self.set_blank_wide_entry(k)
                else:
                    self.set_blank_entry(k)
            else:
                self.set_option_choices(k)
        else:
            k = cvar.split('_')[0]
            self.set_option_entry(k)

root = Tk()
self = ui(root)
#self.add_option_menu('Make', 0)
#self.add_option_menu('Model', 1)
self.add_narrow_option_menu('Make', 0, 0)
self.add_narrow_option_menu('Model', 0, 1)
self.add_entry_box('MinPrice', 2, 0, 'Min $')
self.add_entry_box('MaxPrice', 2, 1, 'Max $')
self.add_narrow_option_menu('MinYear', 3, 0, 'From')
self.add_narrow_option_menu('MaxYear', 3, 1, 'To')
self.add_wide_entry_box('Keywords', 4, 'Keywords, separated by commas')
