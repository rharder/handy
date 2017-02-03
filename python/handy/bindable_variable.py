#!/usr/bin/env python3
"""
Represents a variable that can bind listeners to changes in its state,
similar to the tkinter.StringVar, IntVar, etc classes.

Source: http://github.com/rharder/handy
"""

import logging
from typing import List

import time

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__date__ = "5 Dec 2016"
__license__ = "Public Domain"


class Var(object):
    """
    Represents a variable that can bind listeners to changes in its state.

    Example usage:

        def main():
            x = Var(42, name="answer")
            x.notify(variable_was_changed)
            x.value = 23
            x.value += 100
            x += 1

        def variable_was_changed(var, old_val, new_val):
            print("Variable changed: name={}, old={}, new={}".format(var.name, old_val, new_val))

        if __name__ == "__main__":
            main()

    The output would be:

        Variable changed: name=answer, old=42, new=23
        Variable changed: name=answer, old=23, new=123
        Variable changed: name=answer, old=123, new=124

    When registering with the notify() method, the value_only parameter can be set to True
    (default is False) so that the callback function receives only a single parameter, the
    new value.  This can aid in binding attributes without extra "glue" code:

        x.notify(self.tk_root.wm_title, value_only=True)

    When registering with the notify() method, the no_args parameter can be set to True
    (default is False) so that the callback function will be called with no parameters.

        x.notify(self.something_happened, no_args=True)

    If the value itself is mutable, such as with a list, the fire_notifications() method can
    be used to force a notification to be sent to all listeners.

        a = Var(["cat", "dog", "elephant"], name="pets)
        a.notify(variable_was_changed)
        a.value[2] = "turtle"
        a.fire_notifications()

    In this case the listeners will be called with old_val and new_val being the same:

        Variable changed: name=pets, old=['cat', 'dog', 'turtle'], new=['cat', 'dog', 'turtle']

    A similar effect can be achieved using Python's with construct:

        a = Var(["cat", "dog", "elephant"], name="pets")
        a.notify(variable_was_changed)
        with a:
            a.value[1] = "mouse"
            a.value[2] = "turtle"

        When the with block closes, the fire_notifications method will be called except in the
        following situation.  The with block can also receive a special Exception type that can be
        raised to break out of the with block without notifying listeners:

            with a as unchanged:
                if parents_disapprove():
                    a.value[2] = "turtle"
                else:
                    raise unchanged

        This small example could surely be handled more cleanly with the fire_notifications() method,
        but the with construct is there in case that helps make your design smoother.
    """
    __name_counter = 0

    def __init__(self, value=None, name: str = None):
        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.__value = value

        if name is None:
            self.__name = "Var_{}".format(Var.__name_counter)
            Var.__name_counter += 1
        else:
            self.__name = name

        self.__listeners = []
        self.__values_only = []  # List of listeners who want only the new value as an argument
        self.__no_args = []  # List of listeners who should not receive any arguments

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, new_val):
        """
        Sets the variable's value and notifies listeners if there was a change.

        The listeners will only be notified if old_val != new_val.

        :param new_val: the new value to save in the Var
        """
        self.set(new_val)

    def get(self):
        """ Helper for when the value must be retrieved with a function. """
        return self.value

    def set(self, new_val, force_notify=False):
        """
        Sets the value as an alternative usage to x.value = 42.  Also supports
        the option of forcing the notification of listeners, even when the
        value is not in fact changed.

        :param new_val: The new value for the variable
        :param force_notify: Notify listeners even if the value did not actually change
        """
        old_val = self.__value
        if old_val != new_val or force_notify:
            self.__value = new_val
            self._notify_listeners(old_val, new_val)

    def tk_var(self):
        import tkinter as tk
        tkvar = tk.Variable()
        tkvar.trace("w", lambda _, __, ___, v=tkvar: self.set(tkvar.get()))
        self.add_listener(lambda x: tkvar.set(x), value_only=True)
        return tkvar

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, new_val: str):
        self.__name = new_val

    def add_listener(self, listener, value_only: bool = False, no_args=False):
        """
        Registers listener as a callable object (a function or lambda generally) that will be
        notified when the value of this variable changes.

        The options value_only and no_args are mutually exclusive.  If both are set
        to True, then it is unspecified which form of notification will occur: one
        argument or no arguments.

        :param listener: the listener to notify
        :param bool value_only: listener will be notified with only one argument, the new value
        :param bool no_args: listener will be notified with no arguments
        """
        self.__listeners.append(listener)
        if value_only:
            self.__values_only.append(listener)
        if no_args:
            self.__no_args.append(listener)

    def remove_listener(self, listener):
        """
        Removes listener from the list of callable objects that are notified when the value changes

        :param listener: the listener to remove
        """
        if listener in self.__listeners:
            self.__listeners.remove(listener)
        if listener in self.__values_only:
            self.__values_only.remove(listener)
        if listener in self.__no_args:
            self.__no_args.remove(listener)

    def remove_all_listeners(self):
        """
        Removes all listeners that are registered to be notified when the value changes.
        """
        self.__listeners.clear()
        self.__values_only.clear()
        self.__no_args.clear()

    def fire_notifications(self):
        """
        Forces notifications to be fired regardless of whether or not a change was detected.

        This can be used when the Var's value has internal changes such as with a list:

            a = Var(["cat", "dog", "elephant"])
            a.notify(var_changed)
            a.value[2] = "turtle"
            a.fire_notifications()

        In this case the listeners will be called with old_val and new_val being the same.
        """
        self._notify_listeners(self.value, self.value)

    def _notify_listeners(self, old_val, new_val):
        """
        Internal method to notify the list of listeners.

        :param old_val: previous value
        :param new_val: new value that was set
        """
        for listener in self.__listeners:
            # Arguments: none
            if listener in self.__no_args:
                listener()

            # Arguments: new value only
            elif listener in self.__values_only:
                listener(new_val)

            # Arguments: variable, old value, new value
            else:
                listener(self, old_val, new_val)

    def __enter__(self):
        """ For use with Python's "with" construct. """
        return self.__UnchangedException

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ For use with Python's "with" construct. """
        if exc_type is not self.__UnchangedException:
            self.fire_notifications()
            return False
        else:
            return True

    class __UnchangedException(BaseException):
        """ For use with Python's "with" construct. """
        pass

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return int(self.value)

    def __float__(self) -> float:
        return float(self.value)

    def __bool__(self) -> bool:
        return bool(self.value)

    def __neg__(self):
        return -self.value

    def __pos__(self):
        return +self.value

    def __abs__(self):
        return abs(self.value)

    def __invert__(self):
        return ~self.value

    def __add__(self, other):
        if type(other) is Var:
            return self.value + other.value
        else:
            return self.value + other

    def __sub__(self, other):
        try:
            return self.value - other
        except TypeError:
            return (-other) + self.value

    def __mul__(self, other):
        if type(other) is Var:
            return self.value * other.value
        else:
            return self.value * other

    def __truediv__(self, other):
        if type(other) is Var:
            return self.value / other.value
        else:
            return self.value / other

    def __floordiv__(self, other):
        if type(other) is Var:
            return self.value // other.value
        else:
            return self.value // other

    def __mod__(self, other):
        if type(other) is Var:
            return self.value % other.value
        else:
            return self.value % other

    def __divmod__(self, other):
        if type(other) is Var:
            return divmod(self.value, other.value)
        else:
            return divmod(self.value, other)

    def __pow__(self, other, modulo=None):
        if modulo is None:
            if type(other) is Var:
                return pow(self.value, other.value)
            else:
                return pow(self.value, other)
        else:  # Has modulo
            if type(other) is Var:
                if type(modulo) is Var:
                    return pow(self.value, other.value, modulo.value)
                else:
                    return pow(self.value, other.value, modulo)
            else:  # other not Var
                if type(modulo) is Var:
                    return pow(self.value, other, modulo.value)
                else:
                    return pow(self.value, other, modulo)

    def __iadd__(self, other):
        if hasattr(self.value, "__iadd__"):
            self.value += other
        elif type(other) is Var:
            self.value = self.value + other.value
        else:
            self.value = self.value + other
        return self

    def __isub__(self, other):
        if hasattr(self.value, "__isub__"):
            self.value -= other
        elif type(other) is Var:
            self.value = self.value - other.value
        else:
            self.value = self.value - other
        return self

    def __imul__(self, other):
        if hasattr(self.value, "__imult__"):
            self.value *= other
        elif type(other) is Var:
            self.value = self.value * other.value
        else:
            self.value = self.value * other
        return self

    def __itruediv__(self, other):
        if hasattr(self.value, "__itruediv__"):
            self.value /= other
        elif type(other) is Var:
            self.value = self.value / other.value
        else:
            self.value = self.value / other
        return self

    def __ifloordiv__(self, other):
        if hasattr(self.value, "__ifloordiv__"):
            self.value //= other
        elif type(other) is Var:
            self.value = self.value // other.value
        else:
            self.value = self.value // other
        return self

    def __imod__(self, other):
        if hasattr(self.value, "__imod__"):
            self.value %= other
        elif type(other) is Var:
            self.value = self.value % other.value
        else:
            self.value = self.value % other
        return self


class FormattableVar(Var):
    """
    A bindable variable represented by a string with formatting objects whose values are
    filled in from a list of supplied Var objects.

        v1 = Var("Joe")
        v2 = Var(23)
        fv = FormattableVar("My name is {}, and I am {} years old.", [v1, v2])
        fv.notify(print, value_only=True)
        v2 += 1

    Output would be:

        My name is Joe, and I am 24 years old.
    """

    def __init__(self, str_format: str, bound_vars: List[Var], name=None):
        super().__init__(self, name=name)
        self.__format = str_format
        self.__vars = bound_vars

        for v in bound_vars:
            v.add_listener(self.__var_changed)

        self.__update_format()

    def __var_changed(self, var, old_val, new_val):
        """ Be notified when any underlying variables change. """
        self.__update_format()

    def __update_format(self):
        """ Update the formattable string with new values. """
        var_vals = [v.value for v in self.__vars]
        self.value = self.__format.format(*var_vals)


class BindableDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.__listeners = []
        self.__listeners_by_key = {}
        self._changes = []
        self._timestamps = {}
        self._suspend_notifications = False

    def __getitem__(self, key):
        val = super().__getitem__(key)
        return val

    def __setitem__(self, key, new_val):
        self.set(key, new_val)

    def set(self, key, new_val, force_notify=False, timestamp=None):
        old_val = self.get(key)
        old_timestamp = self._timestamps.get(key, 0)
        now = time.time()

        # Only make change if timestamp is newer
        if timestamp is None or now > old_timestamp:
            self._timestamps[key] = now
            super().__setitem__(key, new_val)

            # Only make notification if value changed
            if old_val != new_val or force_notify:
                # self._changes.append((key, old_val, new_val))
                self._changes.append({"key": key, "action": "update", "old_val": old_val,
                                      "new_val": new_val, "timestamp": now})
                self._notify_listeners()

    def mark_as_changed(self, key, timestamp=None):
        """
        Triggers notification to listeners for a certain key, regardless of
        any change to the key.  The listeners will get their callback with
        both old_val and new_val being the same.

        Can be handy if the key's value is an object with internal changes,
        such as an array or another dictionary.

        :param key: the key to alert listeners to
        """
        val = self.get(key)
        timestamp = timestamp or time.time()
        self._changes.append({"key": key, "action": "update", "old_val": None,
                              "new_val": val, "timestamp": timestamp})
        self._notify_listeners()

    def __repr__(self):
        dictrepr = super().__repr__()
        return "{}({})".format(type(self).__name__, dictrepr)

    def __str__(self):
        return super().__repr__()

    def update(self, *args, **kwargs):
        with self:
            for k, v in dict(*args, **kwargs).items():
                self[k] = v

    def add_listener(self, listener, key=None):
        """
        Registers listener as a callable object (a function or lambda generally) that will be
        notified when the value of this variable changes.

        The options value_only and no_args are mutually exclusive.  If both are set
        to True, then it is unspecified which form of notification will occur: one
        argument or no arguments.

        The listener will be called with four arguments and should have a signature like this:

            def memory_changed(netmem_dict, key, old_val, new_val):
                ...

        :param listener: the listener to notify
        :param key: only send notifications for changes to this key
        """
        if key is None:
            self.__listeners.append(listener)
        else:
            if key not in self.__listeners_by_key:
                self.__listeners_by_key[key] = []
            self.__listeners_by_key[key].append(listener)


    def remove_listener(self, listener, key=None):
        """
        Removes listener from the list of callable objects that are notified when the value changes

        :param listener: the listener to remove
        """
        if key is None:
            if listener in self.__listeners:
                self.__listeners.remove(listener)
        else:
            key_listeners = self.__listeners_by_key.get(key, [])
            if listener in key_listeners:
                key_listeners.remove(listener)

    def remove_all_listeners(self):
        """
        Removes all listeners that are registered to be notified when the value changes.
        """
        self.__listeners.clear()
        self.__listeners_by_key.clear()

    def _notify_listeners(self):
        """
        Internal method to notify the list of listeners.
        """

        if not self._suspend_notifications:
            changes = self._changes.copy()
            self._changes.clear()
            for change in changes:
                if change["action"] == "update":
                    key = change["key"]
                    old_val = change["old_val"]
                    new_val = change["new_val"]
                    # timestamp = change["timestamp"]

                    # Notify "all" and "by key" listeners
                    for listener in self.__listeners.copy():
                        listener(self, key, old_val, new_val)
                    for key_listener in self.__listeners_by_key.get(key, []).copy():
                        key_listener(self, key, old_val, new_val)


    def __enter__(self):
        """ For use with Python's "with" construct. """
        self._suspend_notifications = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ For use with Python's "with" construct. """
        self._suspend_notifications = False
        self._notify_listeners()

    def tk_var(self, key):
        """ Returns a tk.Var object that is two-way bound to a particular key in this dictionary. """
        import tkinter as tk
        tkvar = tk.Variable()
        tkvar.trace("w", lambda _, __, ___, v=tkvar: self.set(key, tkvar.get()))

        # def _listener(bdict, changed_key, old_val, new_val):
        #     if changed_key == key:
        #         tkvar.set(new_val)

        self.add_listener(lambda _, __, ___, new_val: tkvar.set(new_val), key)
        return tkvar

