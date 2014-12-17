from Tkinter import *
from Tkinter import _setit
from myat.ht_connect import ht_connect
import re
from collections import defaultdict

def create_reset_widget(parent, txtstr, command):
    """Inside 'parent', create a subframe with a fixed (disabled) Entry with
    text 'txtstr' inside it, and a Reset button which calls 'command' upon
    activation. Return the subframe."""
    fixed_frame = Frame(parent)
    fixloc = Entry(fixed_frame, width=20, disabledforeground='blue',
        disabledbackground='#cdcdff')
    fixloc.insert(0, txtstr)
    fixloc.configure({'state': 'disabled'})
    fixloc.grid(row=0, column=0, sticky='nsew')
    locreset = Button(fixed_frame, text='Reset', command=command)
    locreset.grid(row=0, column=1, sticky='nsew')
    return fixed_frame

class location(Frame):

    def __init__(self, parent, hc, refine):
        Frame.__init__(self, parent)
        self.parent = parent
        self.hc = hc
        self.refine = refine
        # Title and info boxes are in row 0.
        self.ltitle = Label(self, text='Enter a location', fg='forestgreen',
            anchor=NW, font=('Helvetica', 20))
        self.ltitle.grid(row=0, column=0, sticky='nwes')
        self.linfo = Label(self, text='', fg='darkred', anchor=NE,
            font=('Helvetica 14 italic'))
        self.linfo.grid(row=0, column=1, sticky='nwes')
        # Explanatory labels for search boxes are in row 1.
        self.l1 = Label(self, text='City/province or postal code\n(e.g., "Toronto, ON" or "M5W 1E6")',
            wraplength=220, anchor=W, justify=LEFT)
        self.l2 = Label(self, text='Search within', anchor=SE)
        self.l1.grid(row=1, column=0, sticky='nwes')
        self.l2.grid(row=1, column=1, sticky='nwes')
        # Location entry box and search radius drop-down are in row 2.
        self.locframe = None
        self.sugg = None
        self.reset_location()
        self.oloc = StringVar(self)
        self.oloc.set('100 km')
        self.all_oloc = ['25 km', '50 km', '100 km', '250 km', '500 km',
            '1000 km', 'Provincial', 'Nationwide']
        self.o1 = OptionMenu(self, self.oloc, *self.all_oloc)
        self.o1.grid(row=2, column=1, sticky='nwes')
        self.c1 = Canvas(self, height=1, width=200, bd=1,
            bg='#777777')
        # If they type a partial location, then we'll put a drop-down
        # suggestion menu in row 3.
        # Divider for location area is in row 4.
        self.c1.grid(row=4, column=0, columnspan=2, sticky='nwes')
        self.columnconfigure(0, minsize=220)

    def cleanup(self, x):
        if self.do_search_id:
            self.after_cancel(self.do_search_id)
            self.do_search_id = None

    def keypress(self, event):
        self.event = event
        self.cleanup(None)
        # Search immediately, if they press Return.
        if self.event.keysym == 'Return':
            self.do_search()
        else:
            self.do_search_id = self.after(1000, self.do_search)

    def _show_info(self, tstr=None):
        if tstr is None:
            tstr = ''
        self.linfo.configure({'text': tstr})
        self.linfo.update()

    def do_search(self, *args):
        "Ask for suggestions matching the text in the search box."
        # If it looks like a postal code in the location entry box, use it
        # as-is. Remove all whitespace and upper-case it.
        typed_loc = self.e1.get()
        typed_loc = re.sub(r'\s', '', typed_loc).upper()
        if re.match(r'[A-Z]\d[A-Z]\d[A-Z]\d', typed_loc):
            self.validate_location(typed_loc)
            return
        self.do_search_id = None
        self._show_info('Searching...')
        asugg = self.hc.address_suggest(self.e1.get())
        # Apparently, no valid locations
        if len(asugg) == 0:
            self._show_info()
            self.modify_suggestions()
            return
        if len(asugg) == 1:
            self.modify_suggestions()
            self.validate_location(asugg[0])
            return
        self._show_info()
        self.modify_suggestions(asugg)

    def modify_suggestions(self, asugg=None):
        "Either remove the suggested location drop down, or add/modify it."
        if self.sugg is not None:
            self.sugg.destroy()
            self.sugg = None
        if asugg is None:
            return
        # Returned suggestions seem to be in quotes. Remove them.
        asugg = map(lambda x: x.replace('"', ''), asugg)
        self.suggloc = StringVar(root)
        self.suggstr = 'Pick a location:'
        self.suggloc.set(self.suggstr)
        # When they set the suggested location, take it as gospel.
        self.suggloc.trace('w', self.sugg_set)
        asugg.insert(0, self.suggstr)
        self.sugg = OptionMenu(self, self.suggloc, *asugg)
        self.sugg.grid(row=3, column=0, sticky='nsew')

    def sugg_set(self, *args):
        this_location = self.suggloc.get()
        # If they didn't actually pick one of the suggested locations, instead
        # choosing the 'Pick a location:' string, then do nothing: they have to
        # pick a real location.
        if this_location == self.suggstr:
            return
        self.modify_suggestions()
        # The location had better be valid, to be honest -- it was the website
        # that suggested it to us. But, best to be sure (and also, to get the
        # JSON with the information about that location in it).
        self.validate_location(this_location)

    def _get_proximity(self):
        "Convert the proximity drop-down to meaningful refinement code."
        dist = self.oloc.get()
        # Any number of km (like "100 km") is just "100", in the refinement
        # JSON. "Provincial" is -2, "National" is -1.
        if dist == 'Provincial':
            return -2
        if dist == 'National':
            return -1
        return dist.split()[0]

    def validate_location(self, pcode):
        """Validate a postal code (or city location) by trying to refine it. If
        it returns no error, then it's valid."""
        self._show_info('Searching...')
        self.js = self.hc.refine(SearchLocation=pcode,
            Proximity=self._get_proximity())
        self._show_info()
        if self.js['ErrorCode'] == 0:
            self.fix_location(self.js['SEOSearchLocation'])

    def fix_location(self, locstr):
        """Once we've found a valid location, replace the location entry field
        with a label with the actual location, and a Reset button."""
        self.e1.destroy()
        self.locframe = create_reset_widget(self, locstr, self.reset_location)
        self.locframe.grid(row=2, column=0, sticky='nsew')
        self.refine.new_location(self.js)

    def reset_location(self):
        if self.locframe:
            self.locframe.destroy()
        self.e1 = Entry(self, width=20)
        self.e1.grid(row=2, column=0, sticky='nwes')
        # When a key is pressed, search, after a delay.
        self.do_search_id = None
        self.e1.bind('<Key>', self.keypress)
        self.bind('<Destroy>', self.cleanup)
        self.e1.focus()
        self.refine.disable_all_widgets()

# To build up the search form, define a dictionary entry for each widget.
# - The dictionary key is the name of the field we use in the JSON
#   "SearchOption", which we send to the back end when refining the search.
# - 'wtype' is the type of widget.
# - 'row' defines the row of the search frame grid to place things in.
# - 'column' defines the column.
# - All widgets which occur on the same row are placed inside a subframe.
# - 'dtext' is the default text to display (i.e., when they've not selected a
#   particular value).
#
# In addition to all these static entries, there's a dynamic entry called
# 'state'.
# - When the location is unknown, every widget needs to be in Tk state
#   'disabled'. In that case, the 'state' dictionary entry is also 'disabled'.
# - Once a location is selected, then one of two things can happen:
#   - When a specific value _has_ been chosen for a form value (e.g., suppose
#     they've set the Make to be "Volkswagen"), then the regular widget (like
#     OptionMenu or Entry) is replaced with a Tk Entry widget containing the
#     text of their selection (and that Entry is in Tk state 'disabled'), as
#     well as a Tk Button widget that clears that particular setting (so, e.g.,
#     if they decide they no longer want to search for Volkswagen only).  In
#     that case, the 'state' dictionary entry is 'specific'.
#   - When a specific value has _not_ been chosen, the 'state' dictionary entry
#     is 'any'.
SEARCH_MAP = {
    'Make': {
        'wtype': 'OptionMenu',
        'row': 0,
        'column': 0,
        'dtext': 'Make (any)',
    },
    'Model': {
        'wtype': 'OptionMenu',
        'row': 1,
        'column': 0,
        'dtext': 'Model (any)',
    },
    'MinPrice': {
        'wtype': 'Entry',
        'label': '$ Min',
        'row': 2,
        'column': 0,
    },
    'MaxPrice': {
        'wtype': 'Entry',
        'label': '$ Max',
        'row': 2,
        'column': 1,
    },
    'MinOdometer': {
        'wtype': 'Entry',
        'label': 'Min km',
        'row': 3,
        'column': 0,
    },
    'MaxOdometer': {
        'wtype': 'Entry',
        'label': 'Max km',
        'row': 3,
        'column': 1,
    },
    'BodyStyle': {
        'wtype': 'OptionMenu',
        'row': 4,
        'column': 0,
        'dtext': 'Body Type (any)',
    },
    'MinYear': {
        'wtype': 'OptionMenu',
        'label': 'From',
        'row': 5,
        'column': 0,
        'dtext': 'Min. Year',
    },
    'MaxYear': {
        'wtype': 'OptionMenu',
        'label': 'to',
        'row': 5,
        'column': 1,
        'dtext': 'Max. Year',
    },
    'Transmission': {
        'wtype': 'OptionMenu',
        'row': 6,
        'column': 0,
        'dtext': 'Transmission (any)',
    },
    'FuelType': {
        'wtype': 'OptionMenu',
        'row': 7,
        'column': 0,
        'dtext': 'Fuel Type (any)',
    },
    'Colour': {
        'wtype': 'OptionMenu',
        'row': 8,
        'column': 0,
        'dtext': 'Colour (any)',
    },
}

class refine(Frame):
    def __init__(self, parent, hc):
        Frame.__init__(self, parent)
        self.parent = parent
        self.hc = hc
        # Need to make variable names unique the search form, in order to be
        # able to search on them repeatedly after modifying them.
        self.svi = 0
        self.js = defaultdict(lambda: list())
        self.l = dict()
        self.v = dict()
        self.w = dict()
        self.build_search_frame(None)
        self.disable_all_widgets()

    def disable_all_widgets(self):
        for k in self.w:
            self.w[k].configure({'state': 'disabled'})

    def enable_all_widgets(self):
        for k in self.w:
            self.w[k].configure({'state': 'normal'})

    def _uname(self, st):
        "Seem to need this to make traces on StringVars work right."
        self.svi += 1
        return '%s_%d' % (st, self.svi)

    def vehicle_count(self, vc):
        "Display the vehicle count."
        pass

    def redraw_widget(self, k):
        "For key 'k' from SEARCH_MAP, update or draw the widget."
        d = SEARCH_MAP[k]
        f = self.sf_dict[k]
        # Is the widget drawn yet?
        if 'drawn_state' not in d:
            cnum = 0
            if 'label' in d:
                self.l[k] = Label(f, text=d['label'], width=7, anchor=W)
                self.l[k].configure({'state': 'disabled'})
                self.l[k].grid(row=0, column=0, sticky='ew')
                f.columnconfigure(cnum, {'weight': 1})
                cnum = 1
            if d['wtype'] == 'OptionMenu':
                self.v[k] = StringVar(f, name=self._uname(k))
                self.v[k].set(d['dtext'])
                self.v[k].trace('w', self.search_modified)
                self.w[k] = OptionMenu(f, self.v[k], self.v[k])
            elif d['wtype'] == 'Entry':
                self.w[k] = Entry(f, width=8)
                self.w[k].bind('<Return>', self.search_modified)
            else:
                raise Exception('Unknown widget type "%s"' % d['wtype'])
            self.w[k].grid(row=0, column=cnum, sticky='ew')
            f.columnconfigure(cnum, {'weight': 1})
            return
        # Yes, it's drawn. If its state hasn't changed, do nothing.
        if d['state'] == d['drawn_state']:
            return
        # Otherwise, see what state it's transitioning from and to.
        pass

    def add_to_search(self, index, row, column, columnspan=1, frame=None,
        text=None):
        """For the given 'index' from SEARCH_MAP:
        - If it's _not_ been specified in the search, add an OptionMenu widget
          with all the legal choices, and add a trace when the option is
          modified so we can refine the search.
        - If it _has_ been specified in the search, then simply label it, but
          add a "Reset" button.
        """
        if frame is None:
            frame = self
        if text is None:
            text = '%s (all)' % index
        search_value = self.hc.get_so(SEARCH_MAP[index])
        # Have they specifically set this value?
        if search_value is None:
            # If (e.g.) we're adding the 'Makes" to the search, then create:
            # - self.l['Makes'], a list of all the makes returned by the
            #   refinement.
            # - self.v['Makes'], a StringVar with the currently selected make.
            # - self.w['Makes'], the OptionMenu widget with the makes listed.
            self.l[index] = [text] + sorted(map(lambda x:
                x['Display'], self.js[index]), key=lambda x: x.lower())
            self.v[index] = StringVar(frame, name=self._uname(index))
            self.v[index].set(self.l[index][0])
            self.v[index].trace('w', self.search_modified)
            self.w[index] = OptionMenu(frame, self.v[index], *self.l[index])
        else:
            # It's specifically set. Display it in a disabled Entry with a
            # Reset button.
            self.v[index] = None
            self.w[index] = create_reset_widget(frame, search_value,
                eval('self.reset_' + index.lower()))
        self.w[index].grid(row=row, column=column, columnspan=columnspan,
            sticky='nesw')

    def reset_makes(self, event):
        pass

    def build_search_frame(self, bsc):
        """Create the search frame, with 'bsc' (body style count) vehicles
        found."""

        # Start with an informative frame: Vehicle count, status info, button
        # to plot the vehicles, divider line.
        self.info_frame = Frame(self)
        self.vc_frame = Frame(self.info_frame)
        # Label containing the number of vehicles.
        self.vcount = Label(self.vc_frame, text='', fg='forestgreen',
            anchor=W, font=('Helvetica', 20))
        self.vcount.grid(row=0, column=0, sticky='nw')
        # Label containing the word "vehicles".
        self.vstring = Label(self.vc_frame, text='', anchor=W,
            font='Helvetica 16')
        self.vstring.grid(row=0, column=1, sticky='nws')
        self.vc_frame.grid(row=0, column=0, sticky='nw')
        # Label where information about what's going on will be shown.
        self.sinfo = Label(self.info_frame, text='', fg='darkred', anchor=SE,
            font=('Helvetica 14 italic'))
        self.sinfo.grid(row=0, column=1, sticky='nwes')
        # Click this button to plot the vehicles.
        self.w['Show'] = Button(self.info_frame, text='Show me the vehicles!')
        self.w['Show'].grid(row=1, column=0, columnspan=2, sticky='ns')
        # Divider line between vehicle count things and search frame.
        self.c1 = Canvas(self.info_frame, height=1, width=200, bd=1,
            bg='#777777')
        self.c1.grid(row=2, column=0, columnspan=2, sticky='ew')
        self.info_frame.grid(row=0, column=0, sticky='nsew')

        # In SEARCH_MAP, build up a dictionary of frames, indexed by key.
        # Every widget starts out disabled.
        self.search_frame = Frame(self)
        # sf_dict is short for "search frame dictionary".
        self.sf_dict = dict()
        # For each row, count number of columns.
        self.row_dict = defaultdict(lambda: list())
        for k in SEARCH_MAP:
            d = SEARCH_MAP[k]
            self.row_dict[d['row']].append(d.get('column', 0))
        max_cols = max(map(lambda k: max(self.row_dict[k]), self.row_dict)) + 1
        for k in SEARCH_MAP:
            d = SEARCH_MAP[k]
            self.sf_dict[k] = Frame(self.search_frame)
            # If this row has one column only, make it span all columns.
            cspan = 1
            if len(self.row_dict[d['row']]) == 1:
                cspan = max_cols
            print "%s: row %s, col %s, cpsan %s" % (k, d['row'], d.get('column', 0), cspan)
            d['state'] = 'disabled'
            self.redraw_widget(k)
            self.sf_dict[k].grid(row=d['row'], column=d.get('column', 0),
                columnspan=cspan, sticky='nsew')
        self.search_frame.grid(row=1, column=0, sticky='nsew')

    def update_vehicle_count(self):
        bsc = 0
        for bs in self.js['BodyStyles']:
            bsd = bs['Display']
            bsc += int(bsd.split()[-1][1:-1])
        self.vcount.configure({'text': str(bsc)})
        self.vstring.configure({'text': 'vehicles'})
        self.w['Show'].configure({'state': 'normal'})

    def new_location(self, js):
        """After a new location is entered, build the widgets with the
        information from the refined JSON."""
        self.js = js
        self.update_vehicle_count()
        self.enable_all_widgets()
        for k in self.js:
            if k not in self.w:
                continue
            if self.js[k] is None:
                continue
            if k not in self.v or self.v[k] is None:
                continue
            self.l[k] = ['%s (all)' % k] + sorted(map(lambda x:
                x['Display'], self.js[k]), key=lambda x: x.lower())
            self.v[k].set(self.l[k][0])
            self.w[k]['menu'].delete(0, 'end')
            for l in self.l[k]:
                self.w[k]['menu'].add_command(label=l,
                    command=_setit(self.v[k], l))
            print "-- Have", k

    def search_modified(self, *args):
        pass

root = Tk()

hc = ht_connect()
ref = refine(root, hc)
ref.grid(row=1, column=0, sticky='new')
lo = location(root, hc, ref)
lo.grid(row=0, column=0, sticky=(N, W))
root.columnconfigure(0, {'weight': 1})
root.rowconfigure(0, {'weight': 1})
