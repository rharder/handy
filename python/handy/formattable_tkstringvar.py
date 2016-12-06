#!/usr/bin/env python3
"""
A subclass of tk.StringVar that holds a formattable string that is updated
whenever the list of underyling tk.XxxVars are updated.
"""
import tkinter as tk

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__date__ = "5 Dec 2016"


class FormattableTkStringVar(tk.StringVar):
    """
    An extension of the tk.StringVar that takes a formattable string, eg, "Age: {}" and a list
    of tk.xxxVar objects, and updates the formatted string whenever one of the underlying vars
    is changed.

    Example:

        self.red = tk.IntVar()
        self.green = tk.IntVar()
        self.blue = tk.IntVar()
        self.hex = FormattableTkStringVar("#{:02X}{:02X}{:02X}", [self.red, self.green, self.blue])
        ...
        hex_label = tk.Label(frame, textvariable=self.hex)
    """

    def __init__(self, str_format: str, var_list: [], **kwargs):
        """
        Creates a bindable variable whose string format is up to date with the underlying variables.
        :param str str_format: the string format, eg, "Age: {}"
        :param var_list: the list of tk.xxxVar objects that feed into the string format
        """
        tk.StringVar.__init__(self, **kwargs)
        self.__format = str_format
        self.__vars = var_list

        for v in var_list:
            v.trace("w", self.var_changed)  # Bind to all underlying vars

        self.update_format()  # Set initial value of formatted string

    def var_changed(self, _, __, ___):
        self.update_format()  # Update with new value

    def update_format(self):
        var_vals = [v.get() for v in self.__vars]  # Collect values for all vars
        self.set(self.__format.format(*var_vals))  # Format string, unpacking the format(..) arguments
