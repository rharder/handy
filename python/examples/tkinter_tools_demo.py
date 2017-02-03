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


def demo_bindable_text_area():
    """ Demonstrate BindableTextArea """

    window = tk.Tk()
    window.title("BindableTextArea")

    var = tk.StringVar()
    ba1 = BindableTextArea(window, width=20, height=3, textvariable=var)
    ba1.pack()
    ba2 = BindableTextArea(window, width=20, height=3, textvariable=var)
    ba2.pack()

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
    bind_tk_attribute(label, "bg", var)

    colors = ["light gray", "light blue", "yellow", "green"]
    for color in colors:
        tk.Radiobutton(window, text=color, variable=var, value=color, bg=color).pack()
    var.set(colors[0])

    window.mainloop()


def demo_bind_tk_method():
    window = tk.Tk()
    var = tk.StringVar()
    bind_tk_method(window.title, var)

    tk.Label(window, text="Window title:").pack(pady=10)
    tk.Entry(window, textvariable=var).pack(padx=20, pady=10)

    var.set("Success: demo_bind_tk_method")
    window.mainloop()


if __name__ == "__main__":
    main()
