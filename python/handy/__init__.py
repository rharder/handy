#!/usr/bin/env python3
"""
This package has handy functions and classes that I use in various places.

Example:

    import handy
    v = hand.Var()
    v.notify(print)
    v.value = "hello"


"""

from .bindable_text_area import *
from .bindable_variable import *
from .formattable_tkstringvar import *

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__date__ = "5 Dec 2016"


def bind_tk_attribute(widget, attr_name, tkvar):
    """
    Helper function to bind an arbitrary tk widget attribute to a tk.xxxVar.

    Example:

        window = tk.Tk()
        var = tk.StringVar()
        label = tk.Label(window, text="Change My Background")
        label.pack()
        handy.bind_tk_attribute(label, "bg", var)
        var.set("light blue")
        window.mainloop()

    :param widget: the tk widget to be affected
    :param attr_name: the name of the attribute to bind
    :param tkvar: the variable to bind to
    """
    tkvar.trace("w", lambda _, __, ___, v=tkvar: widget.configure({attr_name: v.get()}))


def bind_tk_method(func, tkvar):
    """
    Helper function to bind an arbitrary method to a tkvar value.

    Example:

        window = tk.Tk()
        var = tk.StringVar()
        handy.bind_tk_method(window.title, var)
        var.set("My New Title")
        window.mainloop()

    :param func: the function to call expecting a single argument
    :param tkvar: the variable to bind to
    """
    tkvar.trace("w", lambda _, __, ___, v=tkvar: func(tkvar.get()))
