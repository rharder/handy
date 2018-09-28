#!/usr/bin/env python3
"""
Example using the base class for Tk apps that will use asyncio.
"""
import asyncio
import os
import queue
import sys
import threading
import time
import tkinter as tk
import traceback
from functools import partial
from typing import Callable, Union, Coroutine

import aiohttp  # pip install aiohttp

from handy.tk_asyncio_base import TkAsyncioBaseApp

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


def main():
    tk_root = tk.Tk()
    _ = ExampleTkAsyncioApp(tk_root)
    tk_root.mainloop()


class ExampleTkAsyncioApp(TkAsyncioBaseApp):
    URL = "http://captive.apple.com"
    PROXY = os.environ.get("https_proxy") or os.environ.get("http_proxy")

    def __init__(self, root: tk.Tk):
        super().__init__(root)
        self.root = root
        self.root.title("Example Tk Asyncio App")

        # Data
        self.status_var = tk.StringVar()

        # View / Control
        self.create_widgets(self.root)

        # Startup
        self.status = "Click connect to begin."

        # async def test_add():
        #
        #     def add(x, y):
        #         return x + y
        #
        #     x = self.tk(add, 2, 3)
        #     print(f"2 + 3 = {x.result()}")
        #
        # self.io(test_add())

        # Demo how to cancel a task scheduled for the tk loop
        async def demo_cancel_tk_tasks():
            for i in range(1, 11):
                x = self.tk(print, i)
                # await asyncio.sleep(0.1)  # If we delay, the queue will get processed before we cancel
                if i % 2 == 1:
                    x.cancel()
                    # Note some odd numbers may still get through!  It's a race!

        self.io(demo_cancel_tk_tasks())

        # Demo an exception being raised and unhandled on the io loop
        async def demo_io_exception():
            await asyncio.sleep(4)
            print("Demoing an exception on the io loop...", flush=True)
            raise Exception("Example exception raised in io loop")

        x = self.io(demo_io_exception())

        # x.cancel()  # Possible to cancel tasks on io loop

        def demo_tk_exception(foo, bar=None):
            print(f"foo={foo}, bar={bar}", flush=True)
            print("Demoing an exception on the tk loop...", flush=True)
            raise Exception("Example exception raised in tk loop")

        self.tk(demo_tk_exception, 42, bar=23)

        def third_thread():
            time.sleep(8)
            print("Demoing scheduling from a third loop...", flush=True)
            self.status = "Scheduling even works with additional threads"

        threading.Thread(target=third_thread, name="Thread-third", daemon=True).start()

    @property
    def status(self):
        return str(self.status_var.get())

    @status.setter
    def status(self, val):
        # Works from any thread
        self.tk(self.status_var.set, str(val))

    async def ioloop_exception_happened(self, extype, ex, tb, func):
        # await super().ioloop_exception_happened(extype, ex, tb, func)
        self.status = f"io loop: {ex}"

    # def tkloop_exception_happened(self, extype, ex, tb, func):
    #     super().tkloop_exception_happened(extype, ex, tb, func)
    #     self.status = f"tk loop: {ex}"

    def create_widgets(self, parent: tk.Misc):
        # Buttons
        btn_connect = tk.Button(parent, text="Connect to http://captive.apple.com", command=self.connect_clicked)
        btn_connect.grid(row=0, column=0, sticky=tk.E, padx=15, pady=15)

        # Status line
        status_line = tk.Frame(parent, borderwidth=2, relief=tk.GROOVE)
        status_line.grid(row=999, column=0, sticky="EW", columnspan=2)
        lbl_status = tk.Label(status_line, textvar=self.status_var)
        lbl_status.grid(row=0, column=1, sticky=tk.W)

    def connect_clicked(self):
        async def _connect():
            # raise Exception("No, don't connect!")
            async with aiohttp.ClientSession() as session:
                async with session.get(self.URL, proxy=self.PROXY) as resp:  # type: aiohttp.ClientResponse
                    text = await resp.text()
                    self.status = text  # Status line
                    self.tk(self.root.title, text)  # Window Title, for kicks

        self.io(_connect())


if __name__ == "__main__":
    main()
