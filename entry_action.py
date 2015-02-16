# Try to make an Entry box which has text in it when it's empty, but otherwise
# displays what the user types.

from Tkinter import *

def entry_key_press(event):
    "Process the event from a key press in an Entry widget."
    e = event.widget
    s = e.get()
    if s == get_empty_text(e):
        e.delete(0, len(s))
        e.configure({'fg': 'black'})

def entry_key_release(event):
    "Process the event from a key release in an Entry widget."
    e = event.widget
    s = e.get()
    if s == '':
        set_empty_text(e)

def entry_button(event):
    "Process the event from a button press in an Entry widget."
    e = event.widget
    s = e.get()
    if s == get_empty_text(e):
        e.icursor(0)

def entry_focus_in(event):
    "Process the event from an Entry widget getting focus."
    e = event.widget
    s = e.get()
    if s == get_empty_text(e):
        e.icursor(0)
        e.select_clear()

def entry_focus_out(event):
    "Process the event from an Entry widget losing focus."
    e = event.widget
    s = e.get()
    if s == '':
        set_empty_text(e)

def get_empty_text(e):
    if e == en[0]:
        return 'Min. Price'
    return 'Max. Price'

def set_empty_text(e):
    e.insert(0, get_empty_text(e))
    e.configure({'fg': 'grey'})
    e.icursor(0)

root = Tk()

en = ['', '']
for i in range(2):
    en[i] = Entry(root, width=16)
    set_empty_text(en[i])
    en[i].bind('<KeyPress>', entry_key_press)
    en[i].bind('<KeyRelease>', entry_key_release)
    en[i].bind('<ButtonRelease>', entry_button)
    en[i].bind('<FocusIn>', entry_focus_in)
    en[i].bind('<FocusOut>', entry_focus_out)
    en[i].pack()
