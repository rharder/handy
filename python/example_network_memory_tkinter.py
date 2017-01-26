#!/usr/bin/env python3
import threading
import tkinter as tk
from tkinter import ttk

import asyncio
import sys

from multiprocessing import Process

import time

import logging

from experimental import NetworkMemory
from handy import BindableTextArea

logging.basicConfig(level=logging.DEBUG)
# logging.getLogger(__name__).setLevel(logging.DEBUG)



class NetMemApp():
    def __init__(self, local_addr, remote_addr, ioloop=None):
        self.window = tk.Tk()
        self.window.title("Network Memory {}".format(local_addr))

        # Data
        self.netmem = NetworkMemory(local_addr=local_addr,
                                    remote_addr=remote_addr,
                                    multicast=True)#, loop=ioloop)
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
        txt_key.grid(row=0, column=1, sticky=tk.W + tk.E)
        lbl_val = tk.Label(self.window, text="Value:")
        lbl_val.grid(row=1, column=0, sticky=tk.E)
        txt_val = tk.Entry(self.window, textvariable=self.val_var)
        txt_val.grid(row=1, column=1, sticky=tk.W + tk.E)
        btn_update = tk.Button(self.window, text="Update Memory", command=self.update_button_clicked)
        btn_update.grid(row=2, column=0, columnspan=2)
        txt_key.bind('<Return>', lambda x: self.update_button_clicked())
        txt_val.bind('<Return>', lambda x: self.update_button_clicked())

        txt_data = BindableTextArea(self.window, textvariable=self.data_var)
        txt_data.grid(row=3, column=0, columnspan=2)

    def update_button_clicked(self):
        print("update_button_clicked")
        key = self.key_var.get()
        val = self.val_var.get()
        self.netmem.set(key, val)

    def memory_updated(self, var, key, old_val, new_val):
        print("memory_updated", var, key, old_val, new_val)
        self.data_var.set(str(self.netmem))


class ThreadedTask(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        # self.queue = queue
        self.loop = None  # type: asyncio.BaseEventLoop

    def run(self):
        print("IO thread", threading.get_ident())
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        print("Running loop on thread", threading.get_ident())
        # self.loop.run_until_complete(self.mem.connect())
        # self.loop.run_forever()
        print("loop stopped")


    def get_loop(self):
        while self.loop is None:
            time.sleep(.01)
        return self.loop
        # time.sleep(5)  # Simulate long running process
        # self.queue.put("Task finished")

def main():
    # program = NetMemApp(local_addr=("225.0.0.1", 9991), remote_addr=("225.0.0.2", 9992))#, ioloop=loop)
    program = NetMemApp(local_addr=("225.0.0.2", 9992), remote_addr=("225.0.0.1", 9991))#, ioloop=loop)

    print("Main thread", threading.get_ident())
    print("Main thread, current event loop:", asyncio.get_event_loop())
    task = ThreadedTask()
    task.start()
    loop = task.get_loop()
    print("IO loop is unique? ", loop != asyncio.get_event_loop())
    program.netmem.connect(loop)

    program.window.mainloop()



    # loop = asyncio.get_event_loop()
    # root = program.window
    # def tk_update():
    #     try:
    #         root.update()
    #     except tk.TclError as e:
    #         if "application has been destroyed" not in e.args[0]:
    #             raise
    #         else:
    #             sys.exit(0)
    #     # loop.call_soon(tk_update)  # or loop.call_later(delay, tk_update)
    #     loop.call_later(0.05, tk_update)
    # tk_update()
    # loop.run_forever()

    # @asyncio.coroutine
    # def run_tk(root, interval=0.05):
    #     try:
    #         while True:
    #             root.update()
    #             yield from asyncio.sleep(interval)
    #     except tk.TclError as e:
    #         if "application has been destroyed" not in e.args[0]:
    #             raise
    #         else:
    #             sys.exit(0)
    # asyncio.ensure_future(run_tk(program.window))
    # asyncio.get_event_loop().run_forever()


    # program.window.mainloop()




if __name__ == "__main__":
    main()
