#!/usr/bin/env python3
"""
Examples of how to use various items in this package.
"""
import tkinter as tk

import handy

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__date__ = "5 Dec 2016"


def main():
    print("Uncomment a function to demonstrate a capability.")
    # demo_bindable_variable()
    # demo_bindable_text_area()
    # demo_formattable_tkstringvar()
    # demo_bind_tk_attribute()
    # demo_bind_tk_method()
    # demo_emulatetkvar()


def demo_bindable_variable():
    """ Demonstrate handy.Var and handy.FormattableVar """

    # Basic manipulations
    print()
    v = handy.Var(42, name="age")
    v.notify(_bindable_var_changed)
    print("::Setting age to 23 ...")
    v.value = 23
    print("::Incrementing age with v.value += 1 ...")
    v.value += 1
    print("::Incrementing age with v += 1 ...")
    v += 1

    # new_value-only notifications
    print()
    v = handy.Var("Title")
    v.notify(print, value_only=True)
    print("::Notification can optionally have one argument, the new value ...")
    v.value = "New Title"

    # No argument notifications
    print()
    v = handy.Var("Something")
    v.notify(print, no_args=True)
    print("::Notification will be called with no arguments ...")
    v.value = "Else"
    print("::Blank line above? Value is now", v.value)

    # Value is itself mutable
    print()
    v = handy.Var()
    v.notify(print)
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
    person_name = handy.Var("Joe")
    person_age = handy.Var(23)
    fv = handy.FormattableVar("{} is {} years old", [person_name, person_age])
    fv.notify(print, value_only=True)
    person_age += 1


def _bindable_var_changed(var, old_val, new_val):
    print("Variable changed: name={}, old_val={}, new_val={}".format(var.name, old_val, new_val))


def demo_bindable_text_area():
    """ Demonstrate handy.BindableTextArea """

    window = tk.Tk()
    window.title("BindableTextArea")

    var = tk.StringVar()
    ba1 = handy.BindableTextArea(window, width=20, height=3, textvariable=var)
    ba1.pack()
    ba2 = handy.BindableTextArea(window, width=20, height=3, textvariable=var)
    ba2.pack()

    var.set("Type something here")

    window.mainloop()


def demo_formattable_tkstringvar():
    window = tk.Tk()
    window.title("FormattableTkStringVar")

    name_var = tk.StringVar()
    age_var = tk.StringVar()
    sentence_var = handy.FormattableTkStringVar("Your name is {}, and you are {} years old.",
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
    label = tk.Label(window, text="demo_bind_tk_attribute")
    label.pack()
    handy.bind_tk_attribute(label, "bg", var)
    var.set("light blue")
    window.mainloop()


def demo_bind_tk_method():
    window = tk.Tk()
    var = tk.StringVar()
    handy.bind_tk_method(window.title, var)
    var.set("demo_bind_tk_method")
    window.mainloop()
#
# def demo_emulatetkvar():
#     window = tk.Tk()
#     var = handy.EmulateTkVar()
#     txt = tk.Entry(window, textvariable=var)
#     txt.pack()
#     txt.value = "txt.value"
#     var.set("txt.set")
#     var.value = 3
#     var.value += 1
#     window.mainloop()



if __name__ == "__main__":
    main()
