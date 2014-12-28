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
        # Have we created the frame yet? If not, create it.
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
        f.grid(row=row, column=0, sticky='ew')
        f.columnconfigure(0, weight=1, minsize=230)
        f.columnconfigure(1, minsize=70)
        f.rowconfigure(0, minsize=35)

    def clear_Make(self):
        self.search_modified('Clear', 'Make', 0)

    def clear_Model(self):
        self.search_modified('Clear', 'Model', 1)

    def clear_Year(self):
        self.search_modified('Clear', 'Year', 2)

    def set_option_choices(self, k):
        print "-- Now here with", k
        self.e[k].grid_remove()
        self.r[k].configure(state='disabled')
        self.legal = ['Select %s' % k]
        for i1 in range(3):
            self.legal.append('%s %s' % (k, i1+1))
        self.v[k].set(self.legal[0])
        self.w[k]['menu'].delete(0, 'end')
        for choice in self.legal:
            self.w[k]['menu'].add_command(label=choice,
                command=_setit(self.v[k], choice))
        self.w[k].grid(row=0, column=0, sticky='ew')
        self.tv[k] = self.v[k].trace('w', self.search_modified)

    def set_entry(self, k):
        print "-- Set entry", k
        self.w[k].grid_remove()
        self.r[k].configure(state='normal')
        self.e[k].delete(0, 'end')
        self.e[k].insert(0, self.v[k].get())
        self.e[k].configure(state='disabled')
        self.e[k].grid(row=0, column=0, sticky='ew')
        self.v[k].trace_vdelete('w', self.tv[k])

    def search_modified(self, *args):
        # The modified OptionMenu is in args[0], but we've appended a nunber to
        # it. Get the key of the modified OptionMenu.
        cvar = args[0]
        print "-- In search_modified", args
        if cvar == 'Clear':
            k = args[1]
            print "-- Reset to", k
            self.set_option_choices(k)
        else:
            k = cvar.split('_')[0]
            self.set_entry(k)

root = Tk()
self = ui(root)
self.add_option_menu('Make', 0)
self.add_option_menu('Model', 1)
self.add_option_menu('Year', 2)
