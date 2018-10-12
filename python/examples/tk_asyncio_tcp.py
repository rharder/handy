#!/usr/bin/env python3
"""
An example of how to use asyncio event loops and tkinter event loops in the same program.

Discussed here: http://blog.iharder.net/2017/02/03/python-asyncio-and-tkinter-together/
UDP Version: http://pastebin.com/PeHHRR4E
TCP Version: http://pastebin.com/ZGeDULR9
"""
import sys
import asyncio
import threading
import tkinter as tk
from functools import partial
sys.path.append("..")
from handy.tk_asyncio_base import TkAsyncioBaseApp

__author__ = "Robert Harder"


def main():
    tk_root = tk.Tk()
    Main(tk_root)
    tk_root.mainloop()


class Main(TkAsyncioBaseApp):
    def __init__(self, tk_root):
        super().__init__(tk_root)
        # Tk setup
        self.lbl_var = tk.StringVar()
        tk_root.title("Tk Asyncio _Demo")
        tk.Label(tk_root, text="Incoming Message, TCP Port 9999:").pack()
        tk.Label(tk_root, textvariable=self.lbl_var).pack()

        # Prepare coroutine to connect server
        self.transport = None  # type: asyncio.StreamWriter

        async def _connect():
            loop = asyncio.get_event_loop()
            await loop.create_server(lambda: self, "127.0.0.1", 9999)

        self.io(_connect())

    def connection_made(self, transport):
        print("connection_made")
        self.transport = transport

    def connection_lost(self, exc):
        print("connection_lost", exc)

    def eof_received(self):
        print("eof_received")

    def data_received(self, data):
        # print("data_received thread:", threading.get_ident(), flush=True)
        data_string = data.decode()
        print("data_received", data_string.strip())
        self.transport.write("RECVD: {}\n".format(data_string).encode())
        self.lbl_var.set(data_string.strip())  # Works even though it's not on main event thread


if __name__ == "__main__":
    main()
