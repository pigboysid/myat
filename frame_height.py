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

class ui(Frame):

    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.parent = parent
        # For frames that enclose UI elements.
        self.f = dict()
        # For selection widgets inside frames.
        self.w = dict()
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
        if k not in self.f:
            self.f[k] = Frame(self.parent, padx=5)
        f = self.f[k]
        # If the variable already exists, destroy it.
        if k in self.tv:
            self.v[k].trace_vdelete('w', self.tv[k])
            del(self.tv[k])
        if k in self.v:
            del(self.v[k])
        self.v[k] = StringVar(f, name=self._uname(k))
        self.v[k].set('Select %s' % k)
        self.tv[k] = self.v[k].trace('w', self.search_modified)
        if k in self.w:
            del(self.w[k])
        self.w[k] = OptionMenu(f, self.v[k], *map(lambda x: '%s %d' % (k, x),
            range(1, 4)))
        self.w[k].grid(row=0, column=0, sticky='ew')
        if k not in self.r:
            self.r[k] = Button(f, text='Clear',
                command=eval('self.clear_%s' % k))
            self.r[k].grid(row=0, column=1)
        self.r[k].configure(state='disabled')
        f.grid(row=row, column=0, sticky='ew')
        f.columnconfigure(0, weight=1, minsize=230)
        f.rowconfigure(0, minsize=35)

    def clear_Make(self):
        self.search_modified('Clear', 'Make', 0)

    def clear_Model(self):
        self.search_modified('Clear', 'Model', 1)

    def clear_Year(self):
        self.search_modified('Clear', 'Year', 2)

    def search_modified(self, *args):
        # The modified OptionMenu is in args[0], but we've appended a nunber to
        # it. Get the key of the modified OptionMenu.
        cvar = args[0]
        if cvar == 'Clear':
            k, row = args[1], args[2]
            self.add_option_menu(k, row)
        else:
            k = cvar.split('_')[0]
            self.r[k].configure(state='normal')
            self.w[k].destroy()
            del(self.w[k])
            self.w[k] = Entry(self.f[k], disabledforeground='blue',
                disabledbackground='#cdcdff')
            self.w[k].insert(0, self.v[k].get())
            self.w[k].configure({'state': 'disabled'})
            self.w[k].grid(row=0, column=0, sticky='ew')

root = Tk()
self = ui(root)
self.add_option_menu('Make', 0)
self.add_option_menu('Model', 1)
self.add_option_menu('Year', 2)
