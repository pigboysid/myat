from Tkinter import *
from myat.ht_connect import ht_connect
from myat.parse_at import parse_at
from myat.canvas import at_graph
import sys

# For every item in the search frame, we have an internal name for it (like
# "Makes" for the make of vehicle). This corresponds to a particular field in
# the JSON "SearchOption", which we send to the back end when refining the
# search (in the case of the vehicle make, it's the "Make" entry). The
# dictionary below maps these two things to one another.
SEARCH_MAP = {
    'Makes': 'Make',
    'Models': 'Model',
    'MinPrice': 'MinPrice',
    'MaxPrice': 'MaxPrice',
    'MinKm': 'MinOdometer',
    'MaxKm': 'MaxOdometer',
    'BodyStyles': 'BodyStyle',
    'FromYears': 'MinYear',
    'ToYears': 'MaxYear',
    'Transmissions': 'Transmission',
    'FuelTypes': 'FuelType',
    'Colours': 'Colour',
}
# Make a version of SEARCH_MAP map with the keys lower-cased.
SEARCH_LCMAP = dict(zip(map(lambda k: k.lower(), SEARCH_MAP),
    SEARCH_MAP.values()))
# Make a reverse map for SEARCH_MAP (from JSON key to our own internal search
# frame key).
SEARCH_RMAP = dict(zip(SEARCH_MAP.values(), SEARCH_MAP.keys()))

class location(Frame):
    def __init__(self, parent, hc):
        Frame.__init__(self, parent, borderwidth=2)
        self.hc = hc
        self.parent = parent
        self.f1 = Frame(self)
        self.l1 = Label(self.f1, text='Location')
        self.l1.pack(side=LEFT)
        self.e1 = Entry(self.f1, width=20)
        self.e1.pack(fill=X, expand=1)
        self.f1.pack(fill=X, expand=1)
        # Frame for location search.
        self.f2 = None
        # Frame for advanced vehicle search.
        self.f3 = None
        # Frame for plotting results.
        self.f4 = None
        # Count for StringVars, to give them unique names.
        self.svi = 0
        self.do_search_id = None
        self.e1.bind('<Key>', self.keypress)
        self.bind('<Destroy>', self.cleanup)

    def cleanup(self, x):
        if self.do_search_id is not None:
            self.after_cancel(self.do_search_id)

    def keypress(self, event):
        if self.do_search_id is not None:
            self.after_cancel(self.do_search_id)
        self.do_search_id = self.after(1000, self.do_search)

    def modify_suggestion_frame(self, action='c'):
        if action == 'c':
            if self.f2 is None:
                self.f2 = Frame(self)
            else:
                for ch in self.f2.children.values():
                    ch.destroy()
        else:
            if self.f2 is not None:
                self.f2.destroy()
                self.f2 = None

    def modify_search_frame(self, action='c'):
        if action == 'c':
            if self.f3 is None:
                self.f3 = Frame(self)
            else:
                for ch in self.f3.children.values():
                    ch.destroy()
        else:
            if self.f3 is not None:
                self.f3.destroy()
                self.f3 = None
            self.hc.initialize_search()

    def modify_plot_frame(self, action='c'):
        if action == 'c':
            if self.f4 is None:
                self.f4 = Frame(self)
            else:
                for ch in self.f4.children.values():
                    ch.destroy()
        else:
            if self.f4 is not None:
                self.f4.destroy()
                self.f4 = None

    def do_search(self, *args):
        self.do_search_id = None
        asugg = self.hc.address_suggest(self.e1.get())
        if len(asugg) > 0:
            asugg = map(lambda x: x.replace('"', ''), asugg)
            self.oloc = StringVar(root)
            self.oloc.set(asugg[0])
            if len(asugg) == 1:
                self.sugg_change()
            else:
                self.modify_suggestion_frame('c')
                self.l2 = Label(self.f2, text='Suggestions')
                self.l2.pack(side=LEFT)
                self.oloc.trace('w', self.sugg_change)
                self.o1 = OptionMenu(self.f2, self.oloc, *asugg)
                self.o1.pack()
                self.f2.pack(fill=X, expand=1)
        else:
            self.modify_suggestion_frame('d')
            self.modify_plot_frame('d')

    def _debug_summary(self, js, do_print=True):
        if do_print:
            print '-- Entries:'
            for k in sorted(filter(lambda k: isinstance(js[k], list), js)):
                dv = sorted(map(lambda x: x['Display'], js[k]))[:5]
                print '%3d %s (%s)' % (len(js[k]), k, dv)
            print 'Count:', js['Count']
        bsc = 0
        for bs in js['BodyStyles']:
            bsd = bs['Display']
            bsc += int(bsd.split()[-1][1:-1])
        if do_print:
            print "Body style count:", bsc
        return bsc

    def sugg_change(self, *args):
        self.e1.delete(0, len(self.e1.get()))
        self.e1.insert(0, self.oloc.get())
        self.search_location = self.oloc.get()
        self.modify_suggestion_frame('d')
        self.modify_plot_frame('d')
        js = self.hc.refine(SearchLocation=self.search_location)
        self.js = js
        if js:
            # How many cars were returned to us in the JSON? You can count the
            # BodyStyles dictionary: look for the strings in the Display entry,
            # which look like "Sedan (1320)", and extract the last number.
            bsc = self._debug_summary(self.js, do_print=False)
            self.modify_search_frame('c')
            self.build_search_frame(bsc)
            self.f3.pack(side=RIGHT, fill=X, expand=1)
        else:
            self.modify_search_frame('d')
            self.modify_plot_frame('d')

    def _uname(self, st):
        "Seem to need this to make traces on StringVars work right."
        self.svi += 1
        return '%s_%d' % (st, self.svi)

    def add_to_search(self, index, row, column, frame=None, text=None):
        """For the given 'index' from SEARCH_MAP:
        - If it's _not_ been specified in the search, add an OptionMenu widget
          with all the legal choices, and add a trace when the option is
          modified so we can refine the search.
        - If it _has_ been specified in the search, then simply label it, but
          add a "Reset" button.
        """
        ivar = index.lower()       # Turn 'Makes' into 'makes'.
        if frame is None:
            frame = self.f3
        search_value = self.hc.get_so(SEARCH_MAP[index])
        # Have they specifically set this value?
        if search_value is None:
            # If (e.g.) we're add the 'Makes' to the search, then create:
            # - self.makes, with a list of all the makes that were returned by
            #   the refinement.
            # - self.v_make, a StringVar with the currently selected make.
            # - self.w_make, the OptionMenu widget with the makes listed.
            vvar = 'v_' + ivar[:-1]    # Turn 'makes' into 'v_make'.
            wvar = 'w_' + ivar[:-1]    # Turn 'makes' into 'w_make'.
            # If the list of allowed values has only one entry, then they've
            # selected that value explicitly. Behave differently in that case.
            setattr(self, ivar, [text] +
                sorted(map(lambda x: x['Display'], self.js[index]),
                key=lambda x: x.lower()))
            setattr(self, vvar, StringVar(frame, name=self._uname(ivar)))
            getattr(self, vvar).set(getattr(self, ivar)[0])
            getattr(self, vvar).trace('w', self.search_modified)
            setattr(self, wvar, OptionMenu(frame, getattr(self, vvar),
                *getattr(self, ivar)))
            # Make the OptionMenu span the entire width of the frame.
            getattr(self, wvar).grid(row=row, column=column, sticky='ew')
        else:
            # Yes: it's specific. Need to create a subframe which contains a
            # label with the specific value, and also the Reset button.
            wvar = 'w_' + ivar[:-1]
            lvar = 'l_' + ivar[:-1]
            rvar = 'r_' + ivar[:-1]
            setattr(self, wvar, Frame(frame))
            this_frame = getattr(self, wvar)
            setattr(self, lvar, Label(this_frame, text=search_value,
                fg='forestgreen'))
            # Expand the label to fill the width of the frame, except for the
            # part with the Reset button.
            getattr(self, lvar).pack(side=LEFT, fill=X, expand=1)
            setattr(self, rvar, Button(this_frame, text='Reset',
                command=eval('self.reset_%s' % ivar)))
            getattr(self, rvar).pack()
            getattr(self, wvar).grid(row=row, column=column, sticky='ew')

    # Ugh. So much boilerplate.
    def reset_makes(self):
        self.search_modified('Reset', SEARCH_MAP['Makes'])

    def reset_models(self):
        self.search_modified('Reset', SEARCH_MAP['Models'])

    def reset_bodystyles(self):
        self.search_modified('Reset', SEARCH_MAP['BodyStyles'])

    def reset_fromyears(self):
        self.search_modified('Reset', SEARCH_MAP['FromYears'])

    def reset_toyears(self):
        self.search_modified('Reset', SEARCH_MAP['ToYears'])

    def reset_transmissions(self):
        self.search_modified('Reset', SEARCH_MAP['Transmissions'])

    def reset_fueltypes(self):
        self.search_modified('Reset', SEARCH_MAP['FuelTypes'])

    def reset_colours(self):
        self.search_modified('Reset', SEARCH_MAP['Colours'])

    def add_box_to_search(self, index, row, column, frame, label):
        lvar = index.lower()
        vvar = 'l_' + lvar
        evar = 'e_' + lvar
        setattr(self, vvar, Label(frame, text=label, width=7))
        getattr(self, vvar).grid(row=row, column=column)
        setattr(self, evar, Entry(frame, width=8))
        getattr(self, evar).grid(row=row, column=column+1)
        # When they press ENTER in the Entry widget, rerun the search.
        getattr(self, evar).bind('<Return>', self.search_modified)

    def build_search_frame(self, bsc):
        self.add_to_search('Makes', row=0, column=0)

        if self.js['Models'] is None:
            self.v_model = StringVar(root)
            self.v_model.set('(Choose a make first)')
            self.w_model = OptionMenu(self.f3, self.v_model,
                self.v_model.get())
            self.w_model.grid(row=1, column=0, sticky='ew')
        else:
            self.add_to_search('Models', row=1, column=0)

        self.fprice = Frame(self.f3)
        self.add_box_to_search('MinPrice', row=0, column=0, frame=self.fprice,
            label='$ Min')
        self.add_box_to_search('MaxPrice', row=0, column=2, frame=self.fprice,
            label='$ Max')
        self.fprice.grid(row=2, column=0, sticky='ew')

        self.fkm = Frame(self.f3)
        self.add_box_to_search('MinKm', row=0, column=0, frame=self.fkm,
            label='Min km')
        self.add_box_to_search('MaxKm', row=0, column=2, frame=self.fkm,
            label='Max km')
        self.fkm.grid(row=3, column=0)

        self.add_to_search('BodyStyles', row=4, column=0,
            text='Body Type (any)')

        self.fyr = Frame(self.f3)
        self.add_to_search('FromYears', row=0, column=0, text='Min. Year',
            frame=self.fyr)
        self.w_fromyear.config(width=12)
        self.fyr_l1 = Label(self.fyr, text='to', width=3)
        self.fyr_l1.grid(row=0, column=1)
        self.add_to_search('ToYears', row=0, column=2, text='Max. Year',
            frame=self.fyr)
        self.w_toyear.config(width=12)
        self.fyr.grid(row=5, column=0, sticky='ew')

        self.add_to_search('Transmissions', row=6, column=0)
        self.add_to_search('FuelTypes', row=7, column=0, text='Fuel Type (any)')
        self.add_to_search('Colours', row=8, column=0,
            text='Exterior Colour (any)')

        self.fplot = Frame(self.f3)
        self.bsc_label = Label(self.fplot, text='Vehicles found: %d' % bsc)
        self.bsc_label.grid(row=0, column=0, sticky='ew')
        self.b_plot = Button(self.fplot, text='Plot!', command=self.do_plot)
        self.b_plot.grid(row=0, column=1, sticky='ew')
        self.fplot.grid(row=9, column=0, sticky='ew')

    def search_modified(self, *args):
        print "-- Search modified with", args
        kw = dict()
        if isinstance(args[0], Event):
            # When an Entry box is modified, figure out which one it is. It
            # appears to be safe to compare widget memory location addresses.
            ewidget = args[0].widget
            evalue = ewidget.get()
            if ewidget == self.e_maxprice:
                kw['MaxPrice'] = evalue
            elif ewidget == self.e_minprice:
                kw['MinPrice'] = evalue
            elif ewidget == self.e_maxkm:
                kw['MaxOdometer'] = evalue
            elif ewidget == self.e_minkm:
                kw['MinOdometer'] = evalue
            else:
                return
        elif isinstance(args[0], str):
            # Two cases: they pressed Reset, or the OptionMenu has changed.
            if args[0] == 'Reset':
                kw[args[1]] = None
            else:
                # Cheesy, but when they choose a value from an OptionMenu, the
                # argument from the "watch" command comes to us as the variable
                # name, followed by underscore and a number. Extract the
                # variable name.
                index = args[0].split('_')[0]
                if index in SEARCH_LCMAP:
                    vstr = getattr(self, 'v_' + index[:-1]).get()
                    # The OptionMenu is either composed of strings and counts
                    # (like "Volkswagen (2140)"), or in the special case of
                    # FromYear and ToYear, just the straight-up year (like
                    # "2012").
                    kwind = SEARCH_LCMAP[index]
                    if '(' not in vstr:
                        kw[kwind] = vstr
                    else:
                        kw[kwind] = vstr[:vstr.rindex('(')].strip()
                else:
                    return
        else:
            return
        print "-- Searching again", kw
        js = self.hc.refine(**kw)
        self.js = js
        if js:
            bsc = self._debug_summary(self.js, do_print=False)
            self.modify_search_frame('c')
            self.build_search_frame(bsc)
            self.f3.pack(fill=X, expand=1)
        else:
            self.modify_search_frame('d')
            self.modify_plot_frame('d')

    def do_plot(self):
        self.modify_plot_frame('c')
        self.parse_at = parse_at()
        html = self.hc.get_vehicles()
        fh = open(self.parse_at.content_file, 'w')
        print >>fh, html
        fh.close()
        self.parse_at.execute()
        self.canvas = at_graph(self.f4)
        self.f4.pack(side=RIGHT, fill=BOTH, expand=1)

root = self = None
def main():
    global root, self
    root = Tk()
    hc = ht_connect()
    self = location(root, hc)
    self.pack(fill=X, expand=1)

main()
