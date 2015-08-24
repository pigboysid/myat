from Tkinter import *
from Tkinter import _setit
from myat.ht_connect import ht_connect
from myat.parse_at import parse_at
from myat.canvas import at_graph
from myat.utils import commafy
import re
from time import sleep
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
    fixed_frame.columnconfigure(0, {'weight': 1})
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
        self.ltitle.grid(row=0, column=0, sticky='nsew')
        self.linfo = Label(self, text='', fg='darkred', anchor=NE,
            font=('Helvetica 14 italic'))
        self.linfo.grid(row=0, column=1, sticky='nsew')
        # Explanatory labels for search boxes are in row 1.
        self.l1 = Label(self, text='City/province or postal code\n(e.g., "Toronto, ON" or "M5W 1E6")',
            wraplength=220, anchor=W, justify=LEFT)
        self.l2 = Label(self, text='Search within', anchor=SE)
        self.l1.grid(row=1, column=0, sticky='nsew')
        self.l2.grid(row=1, column=1, sticky='nsew')
        # Location entry box and search radius drop-down are in row 2.
        self.locframe = None
        self.sugg = None
        self.reset_location()
        self.oloc = StringVar(self)
        self.oloc.set('100 km')
        self.all_oloc = ['25 km', '50 km', '100 km', '250 km', '500 km',
            '1000 km', 'Provincial', 'Nationwide']
        self.o1 = OptionMenu(self, self.oloc, *self.all_oloc)
        self.o1.grid(row=2, column=1, sticky='nsew')
        self.c1 = Canvas(self, height=1, width=200, bd=1,
            bg='#777777')
        # If they type a partial location, then we'll put a drop-down
        # suggestion menu in row 3.
        # Divider for location area is in row 4.
        self.c1.grid(row=4, column=0, columnspan=2, sticky='nsew')
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
        self.refine.enable_all_widgets()
        self.refine.update_search_widgets()

    def reset_location(self):
        if self.locframe:
            self.locframe.destroy()
            self.locframe = None
        self.e1 = Entry(self, width=20)
        self.e1.grid(row=2, column=0, sticky='nsew')
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
# - 'rkey' is the JSON key (in the returned refinement dictionary) with the
#   list of valid strings and values (e.g., "Volkswagen (2234)"). This is used
#   in OptionMenus to provide the list of valid refinements.
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
#     that case, the 'state' dictionary entry is 'fixed'.
#   - When a specific value has _not_ been chosen, the 'state' dictionary entry
#     is 'any'.
SEARCH_MAP = {
    'Make': {
        'wtype': 'OptionMenu',
        'row': 0,
        'column': 0,
        'dtext': 'Make (any)',
        'rkey': 'Makes',
    },
    'Model': {
        'wtype': 'OptionMenu',
        'row': 1,
        'column': 0,
        'dtext': 'Model (any)',
        'rkey': 'Models',
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
        'rkey': 'BodyStyles',
    },
    'MinYear': {
        'wtype': 'OptionMenu',
        'label': 'From',
        'row': 5,
        'column': 0,
        'dtext': 'Min. Year',
        'rkey': 'FromYears',
    },
    'MaxYear': {
        'wtype': 'OptionMenu',
        'label': 'to',
        'row': 5,
        'column': 1,
        'dtext': 'Max. Year',
        'rkey': 'ToYears',
    },
    'Transmission': {
        'wtype': 'OptionMenu',
        'row': 6,
        'column': 0,
        'dtext': 'Transmission (any)',
        'rkey': 'Transmissions',
    },
    'FuelType': {
        'wtype': 'OptionMenu',
        'row': 7,
        'column': 0,
        'dtext': 'Fuel Type (any)',
        'rkey': 'FuelTypes',
    },
    'Colour': {
        'wtype': 'OptionMenu',
        'row': 8,
        'column': 0,
        'dtext': 'Colour (any)',
        'rkey': 'Colours',
    },
}

class refine(Frame):
    def __init__(self, parent, hc, ca):
        Frame.__init__(self, parent)
        self.parent = parent
        self.hc = hc
        self.ca = ca
        self.canvas = None
        # Need to make variable names unique the search form, in order to be
        # able to search on them repeatedly after modifying them.
        self.svi = 0
        self.js = defaultdict(lambda: list())
        # The following dictionaries are all indexed by the keys from
        # SEARCH_MAP.
        #
        # Storage for labels for each search widget, if any.
        self.l = dict()
        # Storage for OptionMenu variables for each search widget, if any.
        self.v = dict()
        # Storage for the result of calling "trace" on an OptionMenu variable.
        self.tv = dict()
        # Storage for search widgets themselves.
        self.w = dict()
        # When a widget is set to a specific value, store the frame containing
        # the specific value and the Reset button.
        self.r = dict()
        self.build_search_frame(None)
        self.disable_all_widgets()

    def disable_all_widgets(self):
        for k in self.w:
            self.w[k].configure({'state': 'disabled'})
        for k in self.l:
            self.l[k].configure({'state': 'disabled'})

    def enable_all_widgets(self):
        for k in self.w:
            self.w[k].configure({'state': 'normal'})
        for k in self.l:
            self.l[k].configure({'state': 'normal'})

    def _uname(self, st):
        "Seem to need this to make traces on StringVars work right."
        self.svi += 1
        return '%s_%d' % (st, self.svi)

    def refinements_by_key(self, rkey):
        if self.hc.refine_dict[rkey] is None:
            return list()
        return map(lambda ent: ent['Display'], self.hc.refine_dict[rkey])

    def redraw_widget(self, k):
        "For key 'k' from SEARCH_MAP, update or draw the widget."
        d = SEARCH_MAP[k]
        f = self.sf_dict[k]

        def searchable_widget():
            cnum = 0
            if 'label' in d:
                self.l[k] = Label(f, text=d['label'], width=7, anchor=W)
                self.l[k].grid(row=0, column=0, sticky='ew')
                f.columnconfigure(cnum, {'weight': 1})
                cnum = 1
            if d['wtype'] == 'OptionMenu':
                if k in self.v:
                    del(self.v[k])
                self.v[k] = StringVar(f, name=self._uname(k))
                self.v[k].set(d['dtext'])
                self.w[k] = OptionMenu(f, self.v[k], self.v[k])
            elif d['wtype'] == 'Entry':
                self.w[k] = Entry(f, width=8)
                self.w[k].bind('<Return>', self.search_modified)
            else:
                raise Exception('Unknown widget type "%s"' % d['wtype'])
            self.w[k].grid(row=0, column=cnum, sticky='ew')
            # Need the line below for widget to span entire width of column.
            f.columnconfigure(cnum, {'weight': 1})

        def add_search_options():
            legal = [d['dtext']] + self.refinements_by_key(d['rkey'])
            # Specifically for the Model, if there are no legal refinements,
            # then the Make has not been set. Indicate this to the user.
            if k == 'Model' and len(legal) == 1:
                legal = ['Model (choose a make first)']
            self.w[k]['menu'].delete(0, 'end')
            if k in self.tv:
                self.v[k].trace_vdelete('w', self.tv[k])
                del(self.tv[k])
            self.v[k].set(legal[0])
            for choice in legal:
                self.w[k]['menu'].add_command(label=choice,
                    command=_setit(self.v[k], choice))
            if len(legal) > 1:
                if k in self.tv:
                    self.v[k].trace_vdelete('w', self.tv[k])
                    del(self.tv[k])
                self.tv[k] = self.v[k].trace('w', self.search_modified)

        # Is the widget drawn yet?
        if 'drawn_state' not in d:
            # Nope: we're in the search form constructor. Set this search term
            # to be in the 'any' (i.e., non-specific) state, and draw the
            # widget.
            d['drawn_state'] = 'any'
            searchable_widget()
            return
        # Yes, it's drawn. Is its current state the same as its drawn state?
        if d['state'] == d['drawn_state']:
            # Yes; if it's an OptionMenu, and if it's in state 'any', then the
            # list of choices in the widget might be different (e.g., if we
            # change any other search field, then the available "Makes"
            # change). Create the new choices in the widget.
            if not (d['state'] == 'any' and d['wtype'] == 'OptionMenu'):
                return
            add_search_options()
            return
        # Otherwise, see what state it's transitioning from and to.
        if d['drawn_state'] == 'any':
            if d['state'] == 'specific':
                # This is going from unspecified to specified. 
                self.w[k].destroy()
                if k in self.v:
                    del(self.v[k])
                # Commafy any dollar value or km value.
                value = self.hc.so_dict[k]
                if value.isdigit() and 'Year' not in k:
                    value = commafy(value)
                if 'dtext' in d:
                    use_value = d['dtext']
                else:
                    use_value = d['label']
                tstr = ("%s: %s" % (use_value, value)).replace(' (any)', '')
                self.r[k] = create_reset_widget(f, tstr,
                        eval('self.reset_'+k))
                self.r[k].grid(row=0, column=0, sticky='nsew')
        elif d['drawn_state'] == 'specific':
            if d['state'] == 'any':
                # This is going from specified to unspecified. 
                self.r[k].destroy()
                searchable_widget()
                add_search_options()
        d['drawn_state'] = d['state']

    def reset_Make(self):
        self.search_modified('Reset', 'Make')

    def reset_Model(self):
        self.search_modified('Reset', 'Model')

    def reset_MinPrice(self):
        self.search_modified('Reset', 'MinPrice')

    def reset_MaxPrice(self):
        self.search_modified('Reset', 'MaxPrice')

    def reset_MinOdometer(self):
        self.search_modified('Reset', 'MinOdometer')

    def reset_MaxOdometer(self):
        self.search_modified('Reset', 'MaxOdometer')

    def reset_BodyStyle(self):
        self.search_modified('Reset', 'BodyStyle')

    def reset_MinYear(self):
        self.search_modified('Reset', 'MinYear')

    def reset_MaxYear(self):
        self.search_modified('Reset', 'MaxYear')

    def reset_Transmission(self):
        self.search_modified('Reset', 'Transmission')

    def reset_FuelType(self):
        self.search_modified('Reset', 'FuelType')

    def reset_Colour(self):
        self.search_modified('Reset', 'Colour')

    def _show_info(self, tstr=None):
        if tstr is None:
            tstr = ''
        self.sinfo.configure({'text': tstr})
        self.sinfo.update()

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
        self.w['Show'] = Button(self.info_frame, text='Show me the vehicles!',
            command=self.do_plot)
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
            self.sf_dict[k] = Frame(self.search_frame, height=100)
            # If this row has one column only, make it span all columns.
            cspan = 1
            if len(self.row_dict[d['row']]) == 1:
                cspan = max_cols
            d['state'] = 'any'
            self.redraw_widget(k)
            self.sf_dict[k].grid(row=d['row'], column=d.get('column', 0),
                columnspan=cspan, sticky='nsew')
        self.search_frame.grid(row=1, column=0, sticky='nsew')

    def update_vehicle_count(self):
        bsc = 0
        for bs in self.hc.refine_dict['BodyStyles']:
            bsd = bs['Display']
            bsc += int(bsd.split()[-1][1:-1])
        self.vcount.configure({'text': str(bsc)})
        self.vstring.configure({'text': 'vehicles'})
        self.w['Show'].configure({'state': 'normal'})

    def update_search_widgets(self):
        """After a new location is entered, build the widgets with the
        information from the refined JSON, which is in self.hc.refine_dict."""
        self.update_vehicle_count()
        for k in SEARCH_MAP:
            d = SEARCH_MAP[k]
            # Is the search parameter (like "Make" or "BodyStyle") specified?
            if self.hc.so_dict[k] is None:
                d['state'] = 'any'
            else:
                d['state'] = 'specific'
            self.redraw_widget(k)

    def search_modified(self, *args):
        print "-- Search modified", args
        kw = dict()
        # Did they type a new value in an Entry box?
        if isinstance(args[0], Event):
            # When an Entry box is modified, figure out which one it is. It
            # appears to be safe to compare widget memory location addresses.
            ewidget = args[0].widget
            k = filter(lambda k: self.w[k] == ewidget, self.w)[0]
            kw[k] = ewidget.get()
        elif isinstance(args[0], str):
            if args[0] == 'Reset':
                kw[args[1]] = None
            else:
                # Cheesy, but when they choose a value from an OptionMenu, the
                # argument from the "watch" command comes to us as the variable
                # name, followed by underscore and a number. Extract the
                # variable name.
                k = args[0].split('_')[0]
                vstr = self.v[k].get()
                # The OptionMenu is either composed of strings and counts (like
                # "Volkswagen (2140)"), or in the special case of FromYear and
                # ToYear, just the straight-up year (like "2012").
                if '(' in vstr:
                    vstr = vstr[:vstr.rindex('(')].strip()
                # If the OptionMenu value is merely the default text (i.e.,
                # if for "Make", it was "Make (any)"), then don't bother
                # searching -- this case happens upon setting the location for
                # the first time.
                dtext = SEARCH_MAP[k]['dtext']
                if not dtext.startswith(vstr):
                    kw[k] = vstr
        if len(kw) == 0:
            return
        self._show_info('Searching...')
        self.hc.refine(**kw)
        if self.hc.refine_dict['ErrorCode'] == 0:
            self._show_info()
            self.update_search_widgets()
        else:
            self._show_info('Search error!')

    def do_plot(self):
        self.parse_at = parse_at()
        html = self.hc.get_vehicles()
        fh = open(self.parse_at.content_file, 'w')
        print >>fh, html
        fh.close()
        self.parse_at.execute()
        if self.canvas:
            self.canvas.destroy()
        self.canvas = at_graph(self.ca)

root = Tk()

hc = ht_connect()
ca = Frame(root)
ca.grid(row=0, rowspan=2, column=1, sticky='nsew')
ref = refine(root, hc, ca)
ref.grid(row=1, column=0, sticky='new')
lo = location(root, hc, ref)
lo.grid(row=0, column=0, sticky=(N, W))

root.columnconfigure(1, {'weight': 1})
root.rowconfigure(1, {'weight': 1})

root.mainloop()
