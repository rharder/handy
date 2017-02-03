#!/usr/bin/env python3
"""
An example of how to use asyncio event loops and tkinter event loops in the same program.
"""
import threading
import tkinter as tk
import asyncio
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
        tk.Label(tk_root, text="Incoming Message, UDP Port 9999:").pack()
        tk.Label(tk_root, textvariable=self.lbl_var).pack()

        # Prepare coroutine to connect server
        self.transport = None  # type: asyncio.DatagramTransport

        @asyncio.coroutine
        def _connect():
            loop = asyncio.get_event_loop()  # Pulls the new event loop because that is who launched this coroutine
            yield from loop.create_datagram_endpoint(lambda: self, local_addr=("0.0.0.0", 9999))

        # Thread that will handle io loop
        def _run(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        ioloop = asyncio.new_event_loop()
        asyncio.run_coroutine_threadsafe(_connect(), loop=ioloop)  # Schedules connection
        t = threading.Thread(target=partial(_run, ioloop))
        t.daemon = True  # won't hang app when it closes
        t.start()  # Server will connect now

    def connection_made(self, transport):
        print("connection_made")
        self.transport = transport

    def connection_lost(self, exc):
        print("connection_lost")

    def datagram_received(self, data, addr):
        data_string = data.decode()
        print("datagram_received", data_string.strip(), addr)
        self.transport.sendto("RECVD: {}".format(data_string).encode(), addr=addr)
        self.lbl_var.set(data_string.strip())

    def error_received(self, exc):
        print("error_received")


if __name__ == "__main__":
    main()
