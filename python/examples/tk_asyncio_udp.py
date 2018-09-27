#!/usr/bin/env python3
"""
An example of how to use asyncio event loops and tkinter event loops in the same program.

Discussed here: http://blog.iharder.net/2017/02/03/python-asyncio-and-tkinter-together/
UDP Version: http://pastebin.com/PeHHRR4E
TCP Version: http://pastebin.com/ZGeDULR9
"""
import threading
import tkinter as tk
import asyncio
from functools import partial

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
        tk_root.title("Tk Asyncio Demo")
        tk.Label(tk_root, text="Incoming Message, UDP Port 9999:").pack()
        tk.Label(tk_root, textvariable=self.lbl_var).pack()

        # Prepare coroutine to connect server
        self.transport = None  # type: asyncio.DatagramTransport

        async def _connect():
            # print("_connect thread:", threading.get_ident(), flush=True)
            loop = asyncio.get_event_loop()  # Pulls the new event loop because that is who launched this coroutine
            await loop.create_datagram_endpoint(lambda: self, local_addr=("0.0.0.0", 9999))

        self.io(_connect())

    def connection_made(self, transport):
        print("connection_made")
        self.transport = transport

    def connection_lost(self, exc):
        print("connection_lost")

    def datagram_received(self, data, addr):
        # print("data_received thread:", threading.get_ident(), flush=True)
        data_string = data.decode()
        print("datagram_received", data_string.strip(), addr)
        self.transport.sendto("RECVD: {}".format(data_string).encode(), addr=addr)
        self.lbl_var.set(data_string.strip())

    def error_received(self, exc):
        print("error_received")


if __name__ == "__main__":
    main()
