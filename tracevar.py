from Tkinter import *

def set_v(*args):
    global v
    print "-- In set_v", args
    print "-- Value is", v.get()

root = Tk()
v = StringVar(root, name='james')
v.set('Value 1')
myt = v.trace('w', set_v)
v.set('Value 2')
v.trace_vdelete('w', myt)
v.set('Value 3')
v.trace('w', set_v)
v.set('Value 4')
