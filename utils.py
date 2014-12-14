import pickle, re
from collections import defaultdict
from math import *

class utils(object):
    """
    Utilities for manipulating the results of a search.
    """

    def __init__(self, pkl_file):
        fh = open(pkl_file, 'rb')
        self.all_descr, self.all_alink, self.all_price, self.all_km, \
            self.all_wheredist, self.all_wherestr = pickle.load(fh)
        fh.close()
        self.all_year = list()
        self.all_make = list()
        self.all_model = list()
        for descr in self.all_descr:
            dsp = descr.split()
            yr, make, model = int(dsp[0]), dsp[1], ' '.join(dsp[2:])
            self.all_year.append(yr)
            self.all_make.append(make)
            self.all_model.append(model)

    def median(self, nlist):
        "Find median of list of numbers, possibly with NaNs in it."
        nlist = filter(lambda x: not isnan(x), nlist)
        ln = len(nlist)
        if ln == 0:
            return float(nan)
        sl = sorted(nlist)
        if ln % 2 == 1:
            return sl[ln / 2]
        return (sl[ln / 2] + sl[ln / 2 - 1]) / 2.0

    def std(self, nlist):
        "Find standard deviation of list of numbers, possibly with NaNs."
        nlist = filter(lambda x: not isnan(x), nlist)
        ln = len(nlist)
        if ln == 0:
            return float(nan)
        if ln == 1:
            return 0
        s = sum(nlist)
        sq = sum(map(lambda x: x*x, nlist))
        return sqrt((sq - s * s / ln) / ln)

    def commafy(self, v):
        "Given numeric v, add comma separators to it and return a string."
        a = str(v)
        # If it appears to be exponential notation, return it as is.
        if 'e' in a:
            return a
        # If there's a decimal place in the number, add it back afterward.
        asp = a.split('.')
        frac = '.' + asp[1] if len(asp) > 1 else ''
        mant = asp[0]
        # If the number has 4 digits, then add one comma.  If it has 7 digits,
        # add two commas. And so on.
        nlen = len(re.search('\d+', mant).group(0))
        for i1 in range(1, (nlen - 1) // 3 + 1):
            sp = -4 * i1 + 1
            mant = mant[:sp] + ',' + mant[sp:]
        return mant + frac

    def axis(self, v1, v2, ntick=4):
        "Given values v1 & v2, find best axis min, max, spacing values."
        # Want at least 4 ticks on the axis.
        vd = v2 - v1
        if vd == 0:
            vd = 1000.0
        if vd < 0:
            vd = -vd
            v1, v2 = v2, v1
        lt = log10(vd * 1.0 / (ntick-1))
        frac = lt - int(lt)
        if frac < log10(2):
            mult = 1.0
        elif frac < log10(5):
            mult = 2.0
        else:
            mult = 5.0
        step = 10 ** int(lt) * mult
        return floor(v1 / step) * step, ceil(v2 / step) * step, step

    def by_year(self):
        "Statistics of price & mileage by year."
        self.km_by_yr = defaultdict(lambda: list())
        self.price_by_yr = defaultdict(lambda: list())
        for yr, price, km in zip(self.all_year, self.all_price, self.all_km):
            self.km_by_yr[yr].append(km)
            self.price_by_yr[yr].append(price)
        print "%13s|%27s|%27s" % ('', 'Mileage', 'Price')
        print "%6s %6s|%6s %6s %6s %6s|%6s %6s %6s %6s" % ('Year', 'Count',
                'Median', 'StdDev', 'Min', 'Max',
                'Median', 'StdDev', 'Min', 'Max',
            )
        for yr in reversed(sorted(self.km_by_yr)):
            k, p = self.km_by_yr[yr], self.price_by_yr[yr]
            print "%6d %6s|%6.0f %6.0f %6.0f %6.0f|%6.0f %6.0f %6.0f %6.0f" \
                % (yr, len(k),
                self.median(k), self.std(k), min(k), max(k),
                self.median(p), self.std(p), min(p), max(p),
                )

#self = utils('atoutput.pkl')
#self.by_year()
