#!/usr/bin/env python3
"""
Demo bindable variable classes
"""

import sys

sys.path.append("..")  # because "examples" directory is sibling to the package
from handy.bindable_variable import Var, FormattableVar, BindableDict


def main():
    demo_bindable_variable()
    demo_bindable_dictionary()


def demo_bindable_variable():
    """ Demonstrate handy.Var and handy.FormattableVar """

    def _bindable_var_changed(var, old_val, new_val):
        print("Variable changed: name={}, old_val={}, new_val={}".format(var.name, old_val, new_val))

    # Basic manipulations
    print()
    v = Var(42, name="age")
    v.add_listener(_bindable_var_changed)
    print("::Setting age to 23 ...")
    v.value = 23
    print("::Incrementing age with v.value += 1 ...")
    v.value += 1
    print("::Incrementing age with v += 1 ...")
    v += 1

    # new_value-only notifications
    print()
    v = Var("Title")
    v.add_listener(print, value_only=True)
    print("::Notification can optionally have one argument, the new value ...")
    v.value = "New Title"

    # No argument notifications
    print()
    v = Var("Something")
    v.add_listener(print, no_args=True)
    print("::Notification will be called with no arguments ...")
    v.value = "Else"
    print("::Blank line above? Value is now", v.value)

    # Value is itself mutable
    print()
    v = Var()
    v.add_listener(print)
    v.value = ["cat", "dog", "elephant"]
    print("::No notification if list item is changed directly ...")
    v.value.append("lion")
    print("::List is now", v.value)
    print("::Notifications happen at end of 'with' construct ...")
    print("::Note that it is not possible to separate old value and new value.")
    with v:
        v.value[2] = "mouse"
        v.value[3] = "gerbil"
        v.value.append("fish")
    print("::An ugly way to abort notifications according to some test ...")
    with v as unchanged:
        if "some truth test":
            raise unchanged
        else:
            v.value.append("chimpanze")

    # Using the FormattableVar
    person_name = Var("Joe")
    person_age = Var(23)
    fv = FormattableVar("{} is {} years old", [person_name, person_age])
    fv.add_listener(print, value_only=True)
    person_age += 1

    # Using tk
    import tkinter as tk
    root = tk.Tk()
    root.title("Bindable Variable")
    v = Var()
    v.add_listener(print, value_only=True)  # echo to console
    entry = tk.Entry(root, textvariable=v.tk_var())  # create a bound tk.Var
    entry.pack()
    v.value = "intial"
    tk.mainloop()


def demo_bindable_dictionary():
    def _bindable_dict_changed(d, key, old_val, new_val):
        print("Dictionary changed: key={}, old_val={}, new_val={}".format(key, old_val, new_val), flush=True)

    d = BindableDict()
    d.add_listener(_bindable_dict_changed)

    d.set("foo", "bar")
    d.set("cats", 4)

    with d:
        d.set("dogs", 0)
        print("before or after?", flush=True)
        d.set("cats", 5)

    a = {"pencil": "yellow", "cup": "full"}
    d.update(a)



if __name__ == "__main__":
    main()
