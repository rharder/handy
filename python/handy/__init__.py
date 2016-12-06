#!/usr/bin/env python3
"""
This package has handy functions and classes that I use in various places.

Example:

    import handy
    v = hand.Var()
    v.notify(print)
    v.value = "hello"


"""

from .tkinter import *
from .bindable_variable import *
from .before_after import *

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__date__ = "5 Dec 2016"
