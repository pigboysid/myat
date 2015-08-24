# Try to make an Entry box which has text in it when it's empty, but otherwise
# displays what the user types.

from Tkinter import *

class at_entry(Frame):

    def __init__(self, parent, empty_text):
        Frame.__init__(self, parent)
        self.parent = parent
        self.w = Entry(self.parent, width=16)
        self.empty_text = empty_text
        self.set_empty_text()
        self.w.bind('<KeyPress>', self.entry_key_press)
        self.w.bind('<KeyRelease>', self.entry_key_release)
        self.w.bind('<ButtonRelease>', self.entry_button)
        self.w.bind('<FocusIn>', self.entry_focus_in)
        self.w.bind('<FocusOut>', self.entry_focus_out)

    def entry_key_press(self, event):
        "Process the event from a key press in an Entry widget."
        e = event.widget
        s = e.get()
        if s == self.empty_text:
            self.w.delete(0, len(s))
            self.w.configure({'fg': 'black'})

    def entry_key_release(self, event):
        "Process the event from a key release in an Entry widget."
        s = self.w.get()
        if s == '':
            self.set_empty_text()

    def entry_button(self, event):
        "Process the event from a button press in an Entry widget."
        s = self.w.get()
        if s == self.empty_text:
            self.w.icursor(0)

    def entry_focus_in(self, event):
        "Process the event from an Entry widget getting focus."
        s = self.w.get()
        if s == self.empty_text:
            self.w.icursor(0)
            self.w.select_clear()

    def entry_focus_out(self, event):
        "Process the event from an Entry widget losing focus."
        s = self.w.get()
        if s == '':
            self.set_empty_text()

    def set_empty_text(self):
        self.w.insert(0, self.empty_text)
        self.w.configure({'fg': 'grey'})
        self.w.icursor(0)

root = Tk()

en = ['', '']
en[0] = at_entry(root, 'Min. Price')
en[0].w.pack()
en[1] = at_entry(root, 'Max. Price')
en[1].w.pack()
