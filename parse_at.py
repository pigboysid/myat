# On my Mac, must invoke this with Python2.7.
#
# To get VW info (this is within 100km (prx=100) of Waterloo, year range 2011
# to present (yRng=2011%2c), 200 cars per page (rcp=200):
#
# http://www.autotrader.ca/a/pv/Used/Volkswagen/Passat/all/?prx=100&cty=Waterloo&prv=Ontario&r=40&loc=Waterloo%2c+ON&cat1=2&cat2=7%2c11%2c10%2c9&yRng=2011%2c&st=1&rcp=200
#
# Replace Volkswagen/Passat with Honda/Accord for Honda instead.

from bs4 import BeautifulSoup
from bs4.element import NavigableString as nstr
from collections import defaultdict
import re, sys, time, pickle
import os.path as op

class model_map(object):
    # Format for model_map is: case-insensitive regex to search for in
    # description, legend string, and chart symbol.

    def __init__(self):

        self.vw_passat = [
            [r'high', 'Highline', 'd'],
            [r'comfort', 'Comfortline', 'x'],
            [r'trend', 'Trendline', 's'],
        ]
        self.honda_accord = [
            [r'\bex-l', 'EX-L', 'd'],
            [r'\bexl', 'EX-L', 'd'],
            [r'\bex', 'EX', '^'],
            [r'\blx', 'LX', 'o'],
            [r'\bse', 'SE', 's'],
        ]
        self.acura_rdx = [
            [r'tech', 'Tech', 'd'],
            [r'\bbase', 'Base', 's'],
        ]
        self.toyota_camry = [
            [r'\bxle', 'XLE', 'd'],
            [r'\ble', 'LE', 'o'],
            [r'\bse\b', 'SE', 's'],
        ]

    def get_mm(self, mm):
        if hasattr(self, mm):
            return getattr(self, mm)
        return list()

class parse_at(object):

    def __init__(self, *args, **kwargs):
        # Legal settings:
        # - content_file: HTML file with results to be parsed.
        # - out_html: prefix of HTML file to be written with results.
        # - title: Graph title (e.g., "Used VW Passats within 100km")
        # - model_map: list of [<regex>, <legendString>, <graphSymbol>] triples
        #   where <regex> is matched against description string.
        self.content_file = 'atoutput.html'
        self.out_html = 'passat.html'
        self.title='2012-2015 VW Passat within 100km of Waterloo'
        self.model_map = []
        self.debug = 0
        self.do_ftp = False
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def execute(self, *queries):
        self.save_content(*queries)
        self.parse_soup(self.content_file)
        #self.plot_results()

    def save_content(self, *args):
        # Pass in one or more HTTP links with queries in them.
        if op.exists(self.content_file):
            file_time = op.getmtime(self.content_file)
            now_time = time.time()
            if now_time - file_time < 86400:
                print "Query results less than 1 day old: not refetching"
                return
        import mechanize
        br = mechanize.Browser()
        fh = open(self.content_file, 'w')
        for qstr in args:
            print "Running query %s..." % qstr
            # Always make there be 500 results per page, sorted low price to
            # high.
            resp = br.open(qstr + "&rcp=500&srt=4")
            print >>fh, resp.read()
        fh.close()

    def parse_soup(self, html_file):
        fh = open(html_file, 'rb')
        content = fh.read()
        fh.close()
        bs = BeautifulSoup(content)
        nc = 0
        self.all_descr = []
        self.all_alink = []
        self.all_price = []
        self.all_km = []
        self.all_wheredist = []
        self.all_wherestr = []
        self.alink_d = dict()
        self.sort_keys = []
        # Count vehicle links, plus vehicles with no price, and no km, and
        # which are duplicates.
        self.vlinks = self.vnoprice = self.vnokm = self.vduplicate = 0
        # Seems like the div with class="at_infoArea" has the string
        # description, plus the link to the actual vehicle page.
        for tag in bs('div', 'at_infoArea'):
            descr = alink = price = km = None
            for child in tag.descendants:
                if isinstance(child, nstr):
                    ch = child.strip()
                    if ch:
                        descr = ch
                        # Gross. Sometimes, <a> link is third parent, not
                        # second.
                        if child.parent.parent.a is not None:
                            alink = child.parent.parent.a['href']
                        else:
                            alink = child.parent.parent.parent.a['href']
                        self.vlinks += 1
                        break
            if descr is None:
                raise ValueError("Couldn't find description string")
            if alink is None:
                raise ValueError("Couldn't find link to vehicle")
            # OK, now look for the div's with class="at_price" and "at_km",
            # inside the parent of the parent.
            price = km = wheredist = wherestr = None
            for child in tag.parent.parent.descendants:
                if isinstance(child, nstr) or child.name != 'div':
                    continue
                chcl = child.get('class')
                if chcl is None:
                    continue
                if chcl[0] == u'at_price':
                    # Don't forget to keep decimal places (people do charge
                    # fractional dollars sometimes).
                    price = int(re.sub(r'[^0-9.]', '',
                        ''.join(child.strings).strip()))
                if chcl[0] == u'at_km':
                    km = int(re.sub(r'[^0-9]', '', child.string.strip()))
                # There are two ResultDistance classes: one just has the city
                # and province, second has the distance as well.  Use the
                # second one.
                if chcl[0] == u'ResultDistance':
                    dstr = ''.join(child.strings).strip().split()
                    # Sometimes, distance string is "In Toronto", others it's
                    # "Within 87 km". Handle both cases.
                    if dstr[0] == 'In':
                        wheredist = 0
                        wherestr = ' '.join(dstr)
                    else:
                        wheredist = int(dstr[1])
                        wherestr = "%s%s" % (dstr[1], dstr[2])
            # Try to remove duplicates from the priority listings: do it by
            # removing the parameters to the URL (i.e., everything after the
            # "?").  The priority listings have one extra parameter.  Also,
            # skip anything which doesn't list a price or a mileage.
            s_alink = re.sub(r'\?.*$', '', alink)
            if price is None:
                self.vnoprice += 1
            elif km is None:
                self.vnokm += 1
            elif s_alink in self.alink_d:
                self.vduplicate += 1
            else:
                self.alink_d[s_alink] = 1
                _uc = lambda st: unicode(st).encode('utf-8')
                self.all_descr.append(_uc(descr))
                self.all_alink.append(alink)
                self.all_price.append(price)
                self.all_km.append(km)
                self.all_wheredist.append(wheredist)
                self.all_wherestr.append(_uc(wherestr))
                # Create a tuple which can be used to sort the list: year, make,
                # model, price, and km.  Also, remember which index number this
                # belongs to.
                # The description string always seems to begin with the year,
                # then the make, then the model.  Split it on space to pull
                # this info out.
                dsplit = descr.split()
                yr, make, model = int(dsplit[0]), dsplit[1], \
                    ' '.join(dsplit[2:])
                self.sort_keys.append((yr, make.lower(), model.lower(), price,
                    km, wheredist, wherestr, len(self.sort_keys)))
                nc += 1
                if self.debug > 1:
                    print "----", nc
                    print descr
                    print alink
                    print s_alink
                    print price
                    print km
        print(("Vehicles: %d, %d good (No price: %d  No mileage: %d  " +
            "Duplicates: %d)") % (self.vlinks, nc, self.vnoprice,
            self.vnokm, self.vduplicate))
        pkl_file = op.splitext(self.content_file)[0] + '.pkl'
        print "-- Using", pkl_file
        fh = open(pkl_file, 'wb')
        pickle.dump([self.all_descr, self.all_alink, self.all_price,
            self.all_km, self.all_wheredist, self.all_wherestr], fh)
        fh.close()

    def plot_results(self):
        import numpy as np
        import matplotlib.pyplot as plt
        plt.rc('legend', labelspacing=0.0, fontsize='medium', loc='best')
        # Colors are by year, from newest to oldest.
        color_order = ['b', 'r', 'm', 'g', 'c', 'y', 'lightgreen', 'brown', 'k']
        # Figure out all distinct years, then map the colors to the year.
        all_year = dict()
        for yr in [x[0] for x in self.sort_keys]:
            all_year[yr] = 1
        for i1, yr in enumerate(reversed(all_year.keys())):
            if i1 >= len(color_order):
                i1 = -1
            all_year[yr] = color_order[i1]

        if self.do_ftp:
            ftp = FTP('aoujw.pair.com')
            ftp.login('jacherry', 'uN3%6aPl')
            ftp.cwd('public_html/newcar')
        # Now, plot graphs of price vs. km.  Do it for 12 different sort
        # orders, six with each ascending and descending:
        # - By year (then price, km, loc_dist).
        # - By make (then price, km, loc_dist).
        # - By model (then price, km, loc_dist).
        # - By price (then year, km, loc_dist).
        # - By km (then year, price, loc_dist).
        # - By location distance (then year, price, km).
        # The self.sort_keys tuple is: (yr, make, model, price, km, loc_dist).
        from operator import itemgetter
        outf_header = '.'.join(self.out_html.split('.')[:-1])
        outf_tail = self.out_html.split('.')[-1]
        header_list = ['Year', 'Make', 'Model', 'Price', 'Mileage', 'Location']
        for tnum, sort_itemsl in enumerate([
            [0, 3, 4, 5],
            [1, 3, 4, 5],
            [2, 3, 4, 5],
            [3, 0, 4, 5],
            [4, 0, 3, 5],
            [5, 0, 3, 4],
        ]):
            sort_items = itemgetter(*sort_itemsl)
            for sort_order in ['ascending', 'descending']:
                this_html = '%s_%s%s.%s' % (outf_header,
                    header_list[tnum].lower()[:2], sort_order[0], outf_tail)
                this_title = ', by %s %s' % (header_list[tnum].lower(),
                    sort_order)
                print "-- Writing '%s'" % this_html
                fig = plt.figure(1)
                fig.clf()
                fig.set_size_inches((12, 9))
                ax = fig.add_subplot(1, 1, 1)
                label_d = dict()
                # When plotting the points, do it in order by reverse year.
                # This is so the legend comes out in the desired order (reverse
                # by year).
                self.sort_keys = sorted(self.sort_keys, key=itemgetter(0),
                        reverse=True)
                for nc, stuple in enumerate(self.sort_keys):
                    yr, i1 = stuple[0], stuple[-1]
                    descr, price, km, wherestr = self.all_descr[i1], \
                        self.all_price[i1], self.all_km[i1], \
                        self.all_wherestr[i1]
                    # Make symbol color depend on year, and marker depend on
                    # model.
                    color = all_year[yr]
                    model = None
                    marker = 'o'
                    for modelm in self.model_map:
                        if re.search(modelm[0], descr, re.I):
                            model = modelm[1]
                            marker = modelm[2]
                            break
                    if model is None:
                        label = "%s" % yr
                    else:
                        label = "%s %s" % (yr, model)
                    if label in label_d:
                        label = None
                    else:
                        label_d[label] = 1
                    xv, yv = km*1e-3, price*1e-3
                    ax.plot(xv, yv, '.', label=label, alpha=0.7, color=color,
                        marker=marker, markersize=8)
                # Now, text labels (and hence, the order of the cars in the
                # table) go on in the sort order we're looping over.
                self.sort_keys = sorted(self.sort_keys, key=sort_items,
                    reverse=(sort_order[0] == 'd'))
                text_d = defaultdict(lambda: [])
                for nc, stuple in enumerate(self.sort_keys):
                    yr, i1 = stuple[0], stuple[-1]
                    descr, price, km, wherestr = self.all_descr[i1], \
                        self.all_price[i1], self.all_km[i1], \
                        self.all_wherestr[i1]
                    color = all_year[yr]
                    xv, yv = int(km), int(price)
                    ttuple = (xv, yv, color, i1)
                    text_d[ttuple].append(str(nc + 1))
                xl = ax.get_xlim()
                yl = ax.get_ylim()
                xp = (xl[1] - xl[0]) * 0.006
                yl = [yl[0], yl[1]]
                yp = yl[1] - yl[0]
                # If any points are too close to the top or bottom edge, expand
                # the y axis to make the points easier to see.
                if (np.min(self.all_price)*1e-3 - yl[0]) / yp <= 0.01:
                    yl[0] = yl[0] - yp*0.04
                if (yl[1] - np.max(self.all_price)*1e-3) / yp <= 0.01:
                    yl[1] = yl[1] + yp*0.04
                ax.set_ylim(yl[0], yl[1])
                # Now we can add the text labels.
                for loc in text_d:
                    xv, yv, color, i1 = loc
                    ax.text(xv*1e-3 + xp, yv*1e-3, ','.join(text_d[loc]),
                        ha='left', va='bottom', fontsize='small', color=color)
                ax.set_ylabel('Price ($000)', fontsize='large')
                ax.set_xlabel('Mileage (km x 1000)', fontsize='large')
                time_str = "This plot was generated on %s" % \
                    (time.strftime('%a %Y-%b-%d at %l:%M%p'))
                ax.set_title(time_str, fontsize='medium')
                fig.suptitle(self.title, fontsize='large')
                ax.legend()
                ax.grid(True)
                pngfile = '%s_%s%s.png' % (outf_header,
                    header_list[tnum].lower(), sort_order[0])
                # I want to build an HTML map for this image so the points are
                # clickable.
                #
                #   http://stackoverflow.com/questions/4668432/how-to-map-
                #     coordinates-in-axesimage-to-coordinates-in-saved-image-
                #     file
                #
                # explains how to do this, so I'm copying their idea.
                # Callbacks didn't seem to work, so I'm being inefficient and
                # drawing the canvas twice (once with a call to draw(), and one
                # with a call to savefig()).
                fig.canvas.draw()
                xl, yl = ax.get_xlim(), ax.get_ylim()
                ll_pixel = ax.transData.transform_point([xl[0], yl[0]])
                ur_pixel = ax.transData.transform_point([xl[1], yl[1]])
                fig.savefig(pngfile, dpi=80)
                fh = open(this_html, 'w')
                print >>fh, "<html><title>%s%s</title></html><body>" % (
                    self.title, this_title)
                # Try to make an image map.  Overlapping points will just have
                # to suffer: let the web browser decide how to handle them.
                print >>fh, '<img src="%s" usemap="#points" />' % (pngfile)
                print >>fh, '<map name="points">'
                xp = [ll_pixel[0], ur_pixel[0]]
                yp = [ll_pixel[1], ur_pixel[1]]
                xd, yd = np.diff(xp), np.diff(yp)
                for loc in text_d:
                    xv, yv, color, i1 = loc
                    alink = self.all_alink[i1]
                    print >>fh, ('<area shape="circle" coords="%d,%d,6" ' +
                        'href="%s">') % (
                        (xv*1e-3 - xl[0])/np.diff(xl)*xd + xp[0],
                        (yl[1] - yv*1e-3)/np.diff(yl)*yd + yp[0],
                        alink)
                print >>fh, '</map><br>'
                # Time to emit a table of call the cars.
                print >>fh, "%d vehicle%s sorted by %s %s, then by %s" % (
                    len(self.all_km),
                    's' if len(self.all_km) != 1 else '',
                    header_list[sort_itemsl[0]].lower(),
                    sort_order, ', '.join([header_list[x].lower()
                        for x in sort_itemsl[1:]]),
                    )
                print >>fh, "<table border=1>"
                print >>fh, "<tr><th>#</th>"
                for i1, hstr in enumerate(header_list):
                    if i1 == tnum:
                        arrowstr = '&uarr;' if sort_order[0] == 'a' \
                            else '&darr;'
                        alink = "<a href='%s_%s%s.%s'>" % (outf_header,
                            hstr.lower()[:2], 'd' if sort_order[0] == 'a'
                            else 'a', outf_tail)
                    else:
                        arrowstr = ''
                        alink = "<a href='%s_%sa.%s'>" % (outf_header,
                            hstr.lower()[:2], outf_tail)
                    print >>fh, "<th>%s%s</a> %s</th>" % (alink, hstr, arrowstr)
                print >>fh, "</tr>"
                for nc, stuple in enumerate(self.sort_keys):
                    i1 = stuple[-1]
                    print >>fh, "<tr>"
                    print >>fh, '<td align=right><a href="%s">%d</a></td>' % \
                        (self.all_alink[i1], nc+1)
                    dsplit = self.all_descr[i1].split()
                    print >>fh, '<td>%s</td><td>%s</td><td>%s</td>' % (
                        dsplit[0], dsplit[1], ' '.join(dsplit[2:]))
                    print >>fh, '<td align=right>$%s</td>' % self.all_price[i1]
                    print >>fh, '<td align=right>%skm</td>' % self.all_km[i1]
                    print >>fh, '<td align=right>%s</td>' % \
                        self.all_wherestr[i1]
                    print >>fh, "</tr>"
                print >>fh, "</table>"
                print >>fh, "</body></html>"
                fh.close()
                if self.do_ftp:
                    # Write files to FTP server.
                    fh = open(this_html, 'r')
                    ftp.storbinary("STOR %s" % this_html, fh)
                    fh.close()
                    fh = open(pngfile, 'rb')
                    ftp.storbinary("STOR %s" % pngfile, fh)
                    fh.close()
        if self.do_ftp:
            ftp.quit()

###############################################################################
# Mainline.
###############################################################################

if False:
    qstr1 = 'http://www.autotrader.ca/a/pv/Used/Volkswagen/Passat/all/?prx=100&cty=Waterloo&prv=Ontario&r=40&loc=Waterloo%2c+ON&cat1=2&cat2=7%2c11%2c10%2c9&yRng=2012%2c&st=1'
    pat = parse_at(
        title='2012-2015 VW Passat within 100km of Waterloo',
        out_html='passat.html',
    )
    pat.execute(qstr1)
elif False:
    qstr1 = 'http://www.autotrader.ca/a/pv/Used/Volkswagen/Jetta/all/?prx=80&cty=Waterloo&prv=Ontario&r=40&loc=Waterloo%2c+ON&cat1=2&cat2=7%2c11%2c10%2c9&yRng=2007%2c2014&st=1'
    qstr1 = 'http://wwwb.autotrader.ca/cars/volkswagen/jetta/on/waterloo/?kwd=TRENDLINE&prx=250&prv=Ontario&loc=n2t2t6&sts=Used&hprc=True&wcp=True'
    pat = parse_at(
        title='VW Jetta Highline within 250km of Waterloo',
        out_html='jetta.html',
    )
    pat.execute(qstr1)
