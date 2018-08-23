#!/usr/bin/env python3
"""
Demo BeforeAndAfter class
"""

import sys

sys.path.append("..")  # because "examples" directory is sibling to the package
from handy.tkinter_tools import *


def main():
    demo_bindable_text_area()
    demo_formattable_tkstringvar()
    demo_bind_tk_attribute()
    demo_bind_tk_method()
    demo_toggled_frame()


def demo_bindable_text_area():
    """ Demonstrate BindableTextArea """

    window = tk.Tk()
    window.title("BindableTextArea")

    var = tk.StringVar()
    ba1 = BindableTextArea(window, width=30, height=5, textvariable=var)
    ba1.pack(fill=tk.BOTH, expand=1)
    ba2 = BindableTextArea(window, width=30, height=5, textvariable=var)
    ba2.pack(fill=tk.BOTH, expand=1)

    var.set("Type something here")

    window.mainloop()


def demo_formattable_tkstringvar():
    window = tk.Tk()
    window.title("FormattableTkStringVar")

    name_var = tk.StringVar()
    age_var = tk.StringVar()
    sentence_var = FormattableTkStringVar("Your name is {}, and you are {} years old.",
                                          [name_var, age_var])

    # Name
    lbl_n = tk.Label(window, text="Name:")
    lbl_n.pack()
    txt_n = tk.Entry(window, textvariable=name_var)
    txt_n.pack()

    # Age
    lbl_a = tk.Label(window, text="Age:")
    lbl_a.pack()
    txt_a = tk.Entry(window, textvariable=age_var)
    txt_a.pack()

    # As a sentence
    sent = tk.Label(window, textvariable=sentence_var)
    sent.pack()

    name_var.set("Joe")
    age_var.set("23")

    window.mainloop()


def demo_bind_tk_attribute():
    window = tk.Tk()

    var = tk.StringVar()

    label = tk.Label(window, text="Background color is bound to variable")
    label.pack()
    bind_tk_var_to_tk_attribute(label, "bg", var)

    colors = ["light gray", "light blue", "yellow", "green"]
    for color in colors:
        tk.Radiobutton(window, text=color, variable=var, value=color, bg=color).pack()
    var.set(colors[0])

    window.mainloop()


def demo_bind_tk_method():
    window = tk.Tk()
    var = tk.StringVar()
    bind_tk_var_to_method(window.title, var)

    tk.Label(window, text="Window title:").pack(pady=10)
    tk.Entry(window, textvariable=var, width=30).pack(padx=40, pady=10)

    var.set("Success: demo_bind_tk_method")
    window.mainloop()


def demo_toggled_frame():
    """ Demonstrate ToggledFrame """

    window = tk.Tk()
    window.title("ToggledFrame")

    # Some arbitrary labels
    f1 = ToggledFrame(window, text="ToggledFrame can be collapsed. Click here.")
    f1.pack(fill=tk.BOTH)
    for i in range(5):
        lbl = tk.Label(f1.subframe, text="Label {}".format(i))
        lbl.pack(fill=tk.BOTH)

    # Some labels and also demonstrate text to show when hidden
    f2 = ToggledFrame(window, text="Here's another")
    f2.pack(fill=tk.BOTH)
    for i in range(2):
        lbl = tk.Label(f2.subframe, text="Label {}".format(i))
        lbl.pack(fill=tk.BOTH)
    # You can have data show up in the collapsed title bar.
    # In this case we're letting the user set it for the demo.
    var = tk.StringVar()
    txt = tk.Entry(f2.subframe, textvariable=var)
    txt.pack(fill=tk.BOTH)
    bind_tk_var_to_property(f2, "hidden_text", var)
    var.set("Data here")

    # Nested frames
    f3 = ToggledFrame(window, text="Nested Frames")
    f3.pack(fill=tk.BOTH)

    def _more(parent, remaining=0):
        if remaining > 0:
            f = ToggledFrame(parent, text="Another ({})".format(remaining))
            f.pack(fill=tk.BOTH)
            _more(f.subframe, remaining - 1)
        else:
            lbl = tk.Label(parent, text="Turtles, all the way down")
            lbl.pack()

    _more(f3.subframe, 3)

    window.mainloop()


if __name__ == "__main__":
    main()
