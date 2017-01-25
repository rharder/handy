#!/usr/bin/env python3


import tkinter as tk
from tkinter import ttk

import asyncio

from experimental import NetworkMemory
from handy import BindableTextArea


class NetMemApp():

    def __init__(self, local_addr, remote_addr):
        self.window = tk.Tk()
        self.window.title("Network Memory {}".format(local_addr))

        # Data
        self.netmem = NetworkMemory(local_addr=local_addr,
                                    remote_addr=remote_addr,
                                    multicast=True)
        self.key_var = tk.StringVar()
        self.val_var = tk.StringVar()
        self.data_var = tk.StringVar()

        # View / Control
        self.create_widgets()

        # Connections
        self.netmem.notify(self.memory_updated)
        pass

    def create_widgets(self):
        lbl_key = tk.Label(self.window, text="Key:")
        lbl_key.grid(row=0, column=0, sticky=tk.E)
        txt_key = tk.Entry(self.window, textvariable=self.key_var)
        txt_key.grid(row=0, column=1, sticky=tk.W+tk.E)
        lbl_val = tk.Label(self.window, text="Value:")
        lbl_val.grid(row=1, column=0, sticky=tk.E)
        txt_val = tk.Entry(self.window, textvariable=self.val_var)
        txt_val.grid(row=1, column=1, sticky=tk.W+tk.E)
        btn_update = tk.Button(self.window, text="Update Memory", command=self.update_button_clicked)
        btn_update.grid(row=2, column=0, columnspan=2)

        txt_data = BindableTextArea(self.window, textvariable=self.data_var)
        txt_data.grid(row=3, column=0, columnspan=2)


    def update_button_clicked(self):
        print("update_button_clicked")
        key = self.key_var.get()
        val = self.val_var.get()
        self.netmem.set(key, val)


    def memory_updated(self, var, key, old_val, new_val):
        print("memory_updated", var, key ,old_val, new_val)
        self.data_var.set(str(self.netmem))

def main():
    program = NetMemApp(local_addr=("225.0.0.1", 9991), remote_addr=("225.0.0.2", 9992))
    # program = NetMemApp(local_addr=("225.0.0.2", 9992), remote_addr=("225.0.0.1", 9991))

    asyncio.ensure_future(run_tk(program.window))
    asyncio.get_event_loop().run_forever()
    # program.window.mainloop()

@asyncio.coroutine
def run_tk(root, interval=0.05):
    try:
        while True:
            root.update()
            yield from asyncio.sleep(interval)
    except tk.TclError as e:
        if "application has been destroyed" not in e.args[0]:
            raise

if __name__ == "__main__":
    main()


