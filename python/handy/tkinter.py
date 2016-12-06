#!/usr/bin/env python3
"""
A collection of functions and classes to help with tkinter.
"""
import tkinter as tk
from tkinter import scrolledtext

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


class BindableTextArea(tk.scrolledtext.ScrolledText):
    """
    A multi-line tk widget that is bindable to a tk.StringVar.

    You will need to import ScrolledText like so:

        from tkinter import scrolledtext
    """

    class _SuspendTrace:
        """ Used internally to suspend a trace during some particular operation. """

        def __init__(self, parent):
            self.__parent = parent  # type: BindableTextArea

        def __enter__(self):
            """ At beginning of operation, stop the trace. """
            if self.__parent._trace_id is not None and self.__parent._textvariable is not None:
                self.__parent._textvariable.trace_vdelete("w", self.__parent._trace_id)

        def __exit__(self, exc_type, exc_val, exc_tb):
            """ At conclusion of operation, resume the trace. """
            self.__parent._trace_id = self.__parent._textvariable.trace("w", self.__parent._variable_value_changed)

    def __init__(self, parent, textvariable: tk.StringVar = None, **kwargs):
        tk.scrolledtext.ScrolledText.__init__(self, parent, **kwargs)
        self._textvariable = None  # type: tk.StringVar
        self._trace_id = None
        if textvariable is None:
            self.textvariable = tk.StringVar()
        else:
            self.textvariable = textvariable
        self.bind("<KeyRelease>", self._key_released)

    @property
    def textvariable(self):
        return self._textvariable

    @textvariable.setter
    def textvariable(self, new_var):
        # Delete old trace if we already had a bound textvariable
        if self._trace_id is not None and self._textvariable is not None:
            self._textvariable.trace_vdelete("w", self._trace_id)

        # Set up new textvariable binding
        self._textvariable = new_var
        self._trace_id = self._textvariable.trace("w", self._variable_value_changed)

    def _variable_value_changed(self, _, __, ___):

        # Must be in NORMAL state to respond to delete/insert methods
        prev_state = self["state"]
        self["state"] = tk.NORMAL

        # Replace text
        text = self._textvariable.get()
        self.delete("1.0", tk.END)
        self.insert(tk.END, text)

        # Restore previous state, whatever that was
        self["state"] = prev_state

    def _key_released(self, evt):
        """ When someone types a key, update the bound text variable. """
        text = self.get("1.0", tk.END)
        with BindableTextArea._SuspendTrace(self):  # Suspend trace to avoid infinite recursion
            if self.textvariable:
                self.textvariable.set(text)
