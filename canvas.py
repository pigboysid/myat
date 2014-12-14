from Tkinter import Tk, Text, BOTH, W, N, E, S, CENTER, Canvas
from ttk import Frame, Button, Label, Style

from myat.utils import utils
import math, webbrowser, re

def resaturate(cstr, pct):
    """Re-saturate a color string, like "#9a86db". pct is a positive number to
    make it less saturated, and negative to make it more saturated."""
    if pct == 0 or cstr[0] != '#' or len(cstr) != 7:
        return cstr
    nstr = '#'
    for i1 in range(3):
        chex = int(cstr[i1*2+1:i1*2+3], 16)
        # Idea is, move each of RGB proportionally away from (or towards) white
        # by the given percentage.
        chex += int(pct * (255 - chex) / 100)
        if chex > 255:
            chex = 255
        elif chex < 0:
            chex = 0
        nstr += '%02x' % chex
    return nstr

class at_graph(Frame):

    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.parent = parent
        self.u = utils('atoutput.pkl')
        self.km = dict()
        self.price = dict()
        self.km[0] = (min(self.u.all_km), max(self.u.all_km))
        self.price[0] = (min(self.u.all_price), max(self.u.all_price))
        self.zoom_level = 0
        try:
            self.parent.title("Auto trader results")
            self.is_standalone = True
        except:
            self.is_standalone = False
        self.style = Style()
        self.style.theme_use("classic")
        # Assume the parent is the root widget; make the frame take up the
        # entire widget size.
        if self.is_standalone:
            self.w, self.h = map(int,
                self.parent.geometry().split('+')[0].split('x'))
        else:
            self.w, self.h = 600, 600
        self.c = None
        # Are they hovering over a data point?
        self.is_hovering = False
        # Filter the description strings: lower and whiten any non-matching
        # data point.
        self.filter = ''
        self.replot()

    def replot(self):
        if self.c is not None:
            self.c.destroy()
        self.c = Canvas(self, height=self.h, width=self.w, bd=1, bg='#f3f5f9')
        self.c.grid(sticky=S, pady=1, padx=1)
        zl = self.zoom_level
        self.axis(self.price[zl], 'y')
        self.axis(self.km[zl], 'x')
        self.car_points()
        self.pack(fill=BOTH, expand=1)

    def xyp(self, x, y):
        "Given x in km and y in $, return canvas position (xp, yp)."
        xp = int(math.floor((1.0 * x - self.x1) / (self.x2 - self.x1) \
            * (self.xp2 - self.xp1) + self.xp1 + 0.5))
        yp = int(math.floor((1.0 * y - self.y1) / (self.y2 - self.y1) \
            * (self.yp2 - self.yp1) + self.yp1 + 0.5))
        return (xp, yp)

    def axis(self, arange, ax):
        "Add an axis ax='x' or 'y', with arange=(min, max) values."
        a1, a2, ast = self.u.axis(*arange)
        nt = int(math.floor((a2 - a1) / ast + 0.5)) + 1
        st_offset = 50
        # Remember the min and max axis values, along with the canvas points
        # that correspond to each location (xp1 and xp2). This allows us to
        # calculate where on the canvas a particular (x, y) value falls.
        if ax == 'x':
            self.x1, self.x2 = a1, a2
            self.xp1, self.xp2 = st_offset, self.w - st_offset
            self.xtick = [a1 + i * ast for i in range(nt)]
            # Remember where the midpoint of the axis is, relative to canvas.
            self.xmid = (self.xp1 + self.xp2) / 2
        else:
            self.y1, self.y2 = a1, a2
            self.yp1, self.yp2 = self.h - st_offset, st_offset
            self.ytick = [a1 + i * ast for i in range(nt)]
            # Remember where the midpoint of the axis is, relative to canvas.
            self.ymid = (self.yp1 + self.yp2) / 2
        # Figure out tick labels.
        atick = ['%g' % ((a1 + i * ast) / 1000) for i in range(nt)]
        # Figure out maximum decimal places on all tick labels, and ensure
        # they all have that many decimal places.
        max_dec = max(map(lambda x: 0 if '.' not in x
            else len(x.split('.')[1]), atick))
        if max_dec > 0:
            atick = map(lambda x: x + '.' + '0'*max_dec if '.' not in x
                else x + '0'*(max_dec - len(x.split('.')[1])), atick)
        yst, xst = self.h - st_offset, st_offset
        # Draw axis line proper, and axis label.
        if ax == 'x':
            self.c.create_line(xst, yst, self.w - st_offset, yst)
            #self.c.create_text(self.w - st_offset + 50, yst - 20,
            #    text='Mileage')
            #self.c.create_text(self.w - st_offset + 50, yst - 5,
            #    text='(km x 1000)')
            xp = (xst + self.w - st_offset) / 2
            self.c.create_text(xp, yst + 30, text='Mileage (km x 1000)')
        else:
            self.c.create_line(xst, yst, xst, st_offset)
            self.c.create_text(xst, st_offset - 30, text='Price')
            self.c.create_text(xst, st_offset - 15, text='($000)')
        tick_anchor = [N, E][ax == 'y']
        tick_x, tick_y = xst, yst
        tick_step = ([self.w, self.h][ax == 'y'] - st_offset * 2 * 1.0) / \
            (nt - 1)
        label_offset = 3
        for i1, tick in enumerate(atick):
            x_of, y_of = -label_offset, label_offset
            if ax == 'y':
                y_of = int(-i1 * tick_step)
            else:
                x_of = int(i1 * tick_step)
            self.c.create_text(tick_x + x_of, tick_y + y_of,
                text=tick, anchor=tick_anchor)
            x_mini, y_mini = 0, 0
            x_maxi, y_maxi = 0, 0
            if ax == 'y':
                x_of += label_offset
                x_mini, x_maxi = 8, self.w - st_offset * 2
                # Remember what y coord this grid line is at.
                if i1 == 0:
                    self.y_grid = []
                self.y_grid.append(tick_y + y_of)
            else:
                y_of -= label_offset
                y_mini, y_maxi = -8, st_offset * 2 - self.h
                # Remember what x coord this grid line is at.
                if i1 == 0:
                    self.x_grid = []
                self.x_grid.append(tick_x + x_of)
            # Draw the little solid tick, next to the axis.
            self.c.create_line(tick_x + x_of, tick_y + y_of,
                tick_x + x_of + x_mini, tick_y + y_of + y_mini)
            # Draw a dashed grid line, across the entire graph.
            self.c.create_line(tick_x + x_of, tick_y + y_of,
                tick_x + x_of + x_maxi, tick_y + y_of + y_maxi,
                dash=(1, 3))

    def car_points(self):
        "Plot the cars themselves."
        color_order = ['#98df8a', '#dbdb8d', '#aec7e8', '#c9acd4', '#f7b6d2',
            '#ffbb80', '#dc9b8d', '#e9ab17', '#dddddd']
        # Those colors above aren't saturated enough. Saturate them more.
        color_order = map(lambda x: resaturate(x, -80), color_order)
        # Change color depending on year.
        cy = dict()
        for i1, year in enumerate(reversed(sorted(set(self.u.all_year)))):
            cy[year] = color_order[-1]
            if i1 < len(color_order):
                cy[year] = color_order[i1]
        i1 = -1
        # Tuples of (index into self.u.all_* arrays, x position, y position).
        self.ov_dict = dict()
        self.c.bind('<Button-1>', func=self.zoom)
        self.c.bind('<Button-2>', func=self.unzoom)
        legend = set()
        osz = 3 + self.zoom_level * 1
        # Total vehicle count, and vehicles which pass the filter count.
        self.vcount = self.fcount = 0
        for year, km, price in zip(self.u.all_year, self.u.all_km,
            self.u.all_price):
            x, y = self.xyp(km, price)
            i1 += 1
            if x < self.x_grid[0] or x > self.x_grid[-1] or \
                y > self.y_grid[0] or y < self.y_grid[-1]:
                continue
            self.vcount += 1
            legend.add((year, cy[year]))
            filtered = False
            if not re.search(self.filter, self.u.all_descr[i1], re.I):
                filtered = True
            # If a data point is filtered out, make its outline reflect its
            # model year, and fill it with white.
            #
            # Else, make its outline and fill color reflect the model year, and
            # upon mouseover, make it entirely red.
            ov = self.c.create_oval(x-osz, y-osz, x+osz, y+osz,
                outline=cy[year],
                activeoutline=['red', cy[year]][filtered],
                fill=[cy[year], 'white'][filtered],
                activefill=['red', 'white'][filtered],
            )
            self.ov_dict[ov] = (i1, x, y, cy[year], filtered)
            # If a data point is filtered out, mousing over it does nothing,
            # and also, lower it behind everything else.
            if filtered:
                self.c.lower(ov)
            else:
                self.fcount += 1
                use_tag = 'Tag %d' % i1
                self.c.addtag_withtag(use_tag, ov)
                self.c.tag_bind(use_tag, sequence='<Enter>',
                    func=self.mouseover)
                self.c.tag_bind(use_tag, sequence='<Leave>',
                    func=self.mouseoff)
                self.c.tag_bind(use_tag, sequence='<Button-1>',
                    func=self.select)
        # OK, add a legend for every year that's displayed.
        i1 = 0
        for yr, color in reversed(sorted(legend)):
            xp, yp = self.x_grid[-1] + 10, self.y_grid[-1] + 15 * i1
            self.c.create_oval(xp-osz, yp-osz, xp+osz, yp+osz,
                outline=color, fill=color)
            self.c.create_text(xp + 8, yp, text=str(yr), anchor=W)
            i1 += 1
        # And, add a title.
        tistr = 'Vehicle count: %d' % self.vcount
        if self.fcount != self.vcount:
            tistr = 'Filtered vehicle count: %d' % self.fcount
        xp = (self.x_grid[0] + self.x_grid[-1]) / 2
        yp = self.y_grid[-1] - 30
        self.c.create_text(xp, yp, text=tistr, font=('Helvetica', '16'))
        zstr1 = 'Click on a blank graph location to zoom in'
        zstr2 = 'Right click to zoom out'
        if self.zoom_level == 0:
            zstr = zstr1
        elif self.zoom_level == 2:
            zstr = zstr2
        else:
            zstr = zstr1 + ', or r' + zstr2[1:]
        self.c.create_text(xp, yp + 16, text=zstr, font=('Helvetica', '14'))

    def mouseover(self, event):
        oval = event.widget.find_closest(event.x, event.y)[0]
        # XXX Sometimes, the closest widget is an axis grid line, not an oval.
        # Need to handle this correctly eventually.
        if oval not in self.ov_dict:
            return
        self.is_hovering = True
        ind, x, y, color, filtered = self.ov_dict[oval]
        # Figure out how high the box needs to be by creating the text off-
        # graph, then getting its bbox and deleting it.
        w = 200
        de_text = self.u.all_descr[ind]
        deobj = self.c.create_text(self.w + 3, self.h + 3, text=de_text,
            anchor=N+W, width=w-6, font=('Helvetica', '14'))
        bbox = self.c.bbox(deobj)
        self.c.delete(deobj)
        h = 18 + bbox[3] - bbox[1]
        border = 5
        if x > self.xmid:
            x -= (w + border)
        else:
            x += border
        if y > self.ymid:
            y -= (h + border)
        else:
            y += border
        self.re = list()
        self.re.append(self.c.create_rectangle(x, y, x + w, y + h,
            fill=resaturate(color, 50)))
        pr_text = '$%s' % self.u.commafy(self.u.all_price[ind])
        self.re.append(self.c.create_text(x + 3, y + 3, text=pr_text,
            anchor=N+W, font=('Helvetica', '10')))
        km_text = '%skm' % self.u.commafy(self.u.all_km[ind])
        self.re.append(self.c.create_text(x + w - 3, y + 3, text=km_text,
            anchor=N+E, font=('Helvetica', '10')))
        wh_text = self.u.all_wherestr[ind]
        if wh_text[0].isdigit():
            wh_text += ' away'
        self.re.append(self.c.create_text(x + w/2, y + 3, text=wh_text,
            anchor=N, font=('Helvetica', '10')))
        self.re.append(self.c.create_text(x + 3, y + 16, text=de_text,
            anchor=N+W, width=w-6, font=('Helvetica', '14')))

    def set_filter(self, st):
        "Given a string 'st', filter ovals whose description doesn't match."
        self.filter = st
        self.replot()

    def mouseoff(self, event):
        "Code for mousing off a data point."
        # The tooptip rectangle and all its sub-objects need to be destroyed.
        map(self.c.delete, self.re)
        # Also, need to note that we're no longer over an oval -- that way,
        # Button-1 events will cause a zoom, rather than launching a web page.
        self.is_hovering = False

    def zoom(self, event):
        # Only zoom in if we're actually within the graph boundaries.
        if event.x <= self.x_grid[0] or event.x > self.x_grid[-1]:
            return
        if event.y >= self.y_grid[0] or event.y < self.y_grid[-1]:
            return
        # Don't zoom if we're hovering over a data point: let the web browser
        # event handler operate.
        if self.is_hovering:
            return
        # Don't zoom in more than twice.
        if self.zoom_level >= 2:
            return
        # Find the grid square which we're inside.
        for i1 in range(len(self.x_grid) - 1):
            if event.x <= self.x_grid[i1 + 1]:
                xgrid = i1 + 1
                break
        for i1 in range(len(self.y_grid) - 1):
            if event.y >= self.y_grid[i1 + 1]:
                ygrid = i1 + 1
                break
        self.zoom_level += 1
        zl = self.zoom_level
        # Make the limits of the new graph be those of the grid square which
        # was clicked inside.
        self.km[zl] = (self.xtick[xgrid-1], self.xtick[xgrid])
        self.price[zl] = (self.ytick[ygrid-1], self.ytick[ygrid])
        self.replot()

    def unzoom(self, event):
        # If already at maximum zoom, nothing to be done.
        if self.zoom_level == 0:
            return
        # If not clicking inside graph boundaries, don't unzoom.
        if event.x <= self.x_grid[0] or event.x > self.x_grid[-1]:
            return
        if event.y >= self.y_grid[0] or event.y < self.y_grid[-1]:
            return
        self.zoom_level -= 1
        self.replot()

    def select(self, event):
        "Open a web page, when a data point has been clicked on."
        oval = event.widget.find_closest(event.x, event.y)[0]
        # XXX As above, sometimes the closest widget is a grid line, not an
        # oval. Need to handle this correctly, eventually.
        if oval not in self.ov_dict:
            return
        ind, xp, yp, color, filtered = self.ov_dict[oval]
        webbrowser.open(self.u.all_alink[ind])

# For running from the command line, change "False" to "True" below.
if False:
    self = None
    root = None

    def main():
        global self, root
      
        root = Tk()
        root.geometry("800x800+0+0")
        self = at_graph(root)
        self.pack(fill=BOTH, expand=1)
        #root.mainloop()  


    if __name__ == '__main__':
        main()  
