#!/usr/bin/env python3
"""
This package has handy functions and classes that I use in various places.

Example:

    import handy
    v = hand.Var()
    v.notify(print)
    v.value = "hello"


"""

from .tkinter_tools import \
    bind_tk_attribute, \
    demo_bind_tk_attribute, \
    BindableTextArea, \
    FormattableTkStringVar
from .bindable_variable import Var, FormattableVar
from .before_after import BeforeAndAfter

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__date__ = "5 Dec 2016"
