#!/usr/bin/env python3
"""
An example of how to use asyncio event loops and tkinter event loops in the same program.

Discussed here: http://blog.iharder.net/2017/02/03/python-asyncio-and-tkinter-together/
UDP Version: http://pastebin.com/PeHHRR4E
TCP Version: http://pastebin.com/ZGeDULR9
"""
import asyncio
import threading
import tkinter as tk
from functools import partial

__author__ = "Robert Harder"


def main():
    tk_root = tk.Tk()
    Main(tk_root)
    tk_root.mainloop()


class Main:
    def __init__(self, tk_root):
        # Tk setup
        self.lbl_var = tk.StringVar()
        tk_root.title("Tk Asyncio Demo")
        tk.Label(tk_root, text="Incoming Message, TCP Port 9999:").pack()
        tk.Label(tk_root, textvariable=self.lbl_var).pack()

        # Prepare coroutine to connect server
        self.transport = None  # type: asyncio.StreamWriter

        async def _connect():
            # print("_connect thread:", threading.get_ident(), flush=True)
            loop = asyncio.get_event_loop()  # Pulls the new event loop because that is who launched this coroutine
            await loop.create_server(lambda: self, "127.0.0.1", 9999)

        # Thread that will handle io loop
        def _run(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        ioloop = asyncio.new_event_loop()
        asyncio.run_coroutine_threadsafe(_connect(), loop=ioloop)  # Schedules connection
        threading.Thread(target=partial(_run, ioloop), daemon=True).start()
        # print("__init__ thread:", threading.get_ident(), flush=True)

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
