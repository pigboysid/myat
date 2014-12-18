import httplib, json, gzip, random, tempfile, os

# This appears to be the JSON sent for a refinement with no other info present.
JS_REFINE = """{"searchOption": {
"BodyStyle":null,
"CarproofOnly":false,
"Category":null,
"Colour":null,
"FuelType":null,
"HasCustomPhoto":true,
"IsRecommended":false,
"Keyword":null,
"LCID":null,
"Make":null,
"MaxHours":null,
"MaxLength":null,
"MaxOdometer":null,
"MaxPrice":null,
"MaxYear":null,
"MicroSite":"",
"MinHours":null,
"MinLength":null,
"MinOdometer":null,
"MinPrice":null,
"MinYear":null,
"Model":null,
"PriceOnly":true,
"Proximity":100,
"RefineCity":false,
"SearchLocation":null,
"ShowCPO":true,
"ShowDamaged":false,
"ShowDealer":true,
"ShowNew":true,
"ShowPrivate":true,
"ShowUsed":true,
"SubType":null,
"Transmission":null,
"Trim":null,
"Type":null
}}"""

class ht_connect(object):

    host = 'wwwb.autotrader.ca'
    # Route to pass some characters, like "Waterl", to have it return location
    # suggestions (like "Waterloo, ON" and "Waterloo, QC").
    suggest_route = '/SuggestionService.asmx/GetLocationSuggestions'
    # Route to pass search criteria, to have it return the number of vehicles
    # which match the criteria.
    refine_route = '/WebServices/ResultsRefinement.svc/GetRefinements'

    def __init__(self):
        # Seems as though we have to manage the connection ourselves. Maintain
        # the cookies which seem to be part of the actual connection.
        #
        # UAG appears to be a unique identifier of 64 hex chars. It seems to
        # get replaced by a server-provided one after the first request, but
        # I'm including it anyway.
        uag = ''.join(['%08X' % x for x in random.sample(xrange(1L<<32), 8)])
        self.cookie_dict = {
            '59_MVT': 'Beta',
            'uag': uag,
        }
        # Dictionary for HTTP headers.
        self.hdict = dict()
        self.hc = httplib.HTTPConnection(self.host)
        # Set initial cookies.
        self._basic_headers()
        self._cookie_headers()
        # Upon construction, get main page, which will return a bunch of
        # Set-Cookie: headers which we should parse, and honor.
        self.hc.request('GET', '/', '', self.hdict)
        r = self.hc.getresponse()
        if r.status != 200:
            raise Exception('Connection to server returned %s error',
                r.status)
        # Have to parse the response, or else can't issue another request.
        self._parse_response(r)
        # Start the search with no options set.
        self.initialize_search()

    def initialize_search(self):
        # Reset the SearchOption dictionary.
        self.so_dict = json.loads(JS_REFINE)['searchOption']
        # And, reset the JSON response (which is a Python representation of the
        # JSON we got back when we refined our results).
        self.js_response = None

    def _basic_headers(self):
        """Define basic HTTP headers: make our browser look like Firefox on a
        Mac, among other things."""
        self.hdict = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:33.0) Gecko/20100101 Firefox/33.0',
            'Referer': 'http://' + self.host,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
        }

    def _cookie_headers(self):
        "Make an HTTP 'Cookie:' header from self.cookie_dict."
        self.hdict['Cookie'] = '; '.join(map(lambda k: k[0] + '=' + k[1],
            self.cookie_dict.iteritems()))

    def _parse_response(self, r):
        "Extract important headers in an HTTP response 'r'."
        # Store _all_ HTTP headers in a dictionary.
        self.hrdict = dict(r.getheaders())
        self.ct = self.hrdict.get('content-type')
        self.ce = self.hrdict.get('content-encoding')
        # There can be multiple Set-Cookie headers.
        # - Get the cookies using the # getallmatchingheaders() method.
        # - Remove the "Set-Cookie: " from the start and "\r\n" from the end.
        # - Remove all the semicolon-separated qualifiers on the cookie like
        #   "path=/' and "HttpOnly". I should probably be parsing "path" and
        #   handling it correctly, but doesn't seem to be critical yet.
        all_sc = map(lambda h: h[12:-2].split(';')[0],
            r.msg.getallmatchingheaders('set-cookie'))
        # Update our cookie dictionary with any new cookies. Note that, e.g., we
        # can get a cookie that replaces our 'uag' cookie -- that's why we're
        # storing these in a dictionary, so that we can silently override any
        # cookies we already have.
        for set_cookie in all_sc:
            scsp = set_cookie.split('=')
            k, v = scsp[0], '='.join(scsp[1:])
            self.cookie_dict[k] = v
        # Seems you always need to read the body of the response, or else you
        # can't make another request.
        self.res = r.read()
        # Might as well unzip it here, if need be.
        if len(self.res) and self.ce == 'gzip':
            # Gross. If gzip, have to write it as a file before decompression.
            tf = tempfile.NamedTemporaryFile(delete=False)
            fname = tf.name
            tf.write(self.res)
            tf.close()
            fh = gzip.open(fname, 'rb')
            self.res = fh.read()
            fh.close()
            os.unlink(fname)

    def _parse_json_body(self, r):
        """Extract JSON from the body of a response 'r', after we've issued a
        POST request and we've parsed out its headers."""
        self.js_response = None
        if len(self.res) == 0 or 'json' not in self.ct:
            return
        try:
            self.js_response = json.loads(self.res)
        except ValueError:
            print "Bad JSON"

    def address_suggest(self, st):
        """Given typed characters 'st', like 'Waterl', call the address
        suggestion service."""
        # Not sure what these headers do, but I think I need them.
        self.hdict['X-NewRelic-ID'] = 'UgUPVV5SGwACU1ZRBAg='
        self.hdict['X-Requested-With'] = 'XMLHttpRequest'
        self.hdict['Content-Type'] = 'application/json; charset=utf-8'
        self._cookie_headers()
        js = json.dumps({'prefixText': st, 'count': 10})
        self.hc.request('POST', self.suggest_route, js, self.hdict)
        r = self.hc.getresponse()
        if r.status != 200:
            raise Exception('Connection to server returned %s error',
                r.status)
        self._parse_response(r)
        self._parse_json_body(r)
        if self.js_response is None:
            return []
        # {u'd': [u'"Waterloo, ON"', u'"Waterloo, QC"']} is how a response
        # looks (presuming we typed "waterl" into the location search box).
        return self.js_response['d']

    def get_so(self, so):
        """Given search option 'so' (like 'MaxOdometer'), return the value
        from the JSON response ['d']['SearchOption'] dictionary, or None if
        there is no value."""
        if self.js_response is None:
            return None
        # Better signal if the JSON response doesn't look like we expect.
        if 'd' not in self.js_response:
            raise ValueError("No 'd' key in JSON response")
        if 'SearchOption' not in self.js_response['d']:
            raise ValueError("No 'SearchOption' key in JSON response")
        if so not in self.js_response['d']['SearchOption']:
            raise ValueError("Missing '%s' key in JSON response" % so)
        return self.js_response['d']['SearchOption'][so]

    def refine(self, **kwargs):
        "Call the vehicle refinement service, with the given dict keys."
        # Upon changing search location, reset search options.
        if 'SearchLocation' in kwargs:
            self.so_dict = json.loads(JS_REFINE)['searchOption']
        for k, v in kwargs.iteritems():
            self.so_dict[k] = v
        self.hdict['X-NewRelic-ID'] = 'UgUPVV5SGwACU1ZRBAg='
        self.hdict['X-Requested-With'] = 'XMLHttpRequest'
        self.hdict['Content-Type'] = 'application/json; charset=utf-8'
        self._cookie_headers()
        js = json.dumps({'searchOption': self.so_dict})
        self.hc.request('POST', self.refine_route, js, self.hdict)
        r = self.hc.getresponse()
        if r.status != 200:
            raise Exception('Connection to server returned %s error',
                r.status)
        self._parse_response(r)
        self._parse_json_body(r)
        if self.js_response is None:
            self.refine_dict = dict()
        else:
            self.refine_dict = self.js_response['d'].copy()
        return self.refine_dict

    def get_vehicles(self):
        rpage = '/cars/volkswagen/on/waterloo/?prx=100&prv=Ontario&loc=waterloo%2c+on&sts=New-Used&hprc=True&wcp=True'
        rpage = self.js_response['d']['ResultPageUrl'] + '&rcp=500&srt=4'
        print rpage
        for key in ['X-NewRelic-ID', 'X-Requested-With', 'Content-Type',
            'Content-Length']:
            if key in self.hdict:
                del(self.hdict[key])
        #self.hdict['Referer'] = 'http://' + self.host + '/Result/AdvancedSearch.aspx?cat1=2&cat2=7%2c11%2c10%2c9&prx=100&prbr=ON&cty=Waterloo&loc=waterloo%2c+on&sts=New-Used&hprc=True&wcp=True&st=1'
        self._cookie_headers()
        self.hc.request('GET', rpage, '', self.hdict)
        r = self.hc.getresponse()
        if r.status != 200:
            raise Exception('Connection to server returned %s error',
                r.status)
        self._parse_response(r)
        # Return the raw HTML.
        return self.res
