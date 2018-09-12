#!/usr/bin/env python3
"""

"""
import asyncio
import json
import logging
import os
import pprint
import threading
import tkinter as tk
import webbrowser
from functools import partial

import aiohttp
from aiohttp import web, WSMsgType

from handy.tkinter_tools import BindableTextArea
from handy.websocket_client import WebsocketClient
from handy.websocket_server import WebServer, WebHandler, WebsocketHandler

__author__ = "Robert Harder"

ECHO_WS_URL = "wss://demos.kaazing.com/echo"
PROXY = os.environ.get("https_proxy") or os.environ.get("http_proxy")

def main():
    tk_root = tk.Tk()
    MainApp(tk_root)
    tk_root.mainloop()


class MainApp:
    def __init__(self, root):
        self.window = root
        root.title("Websocket Example")
        self.log = logging.getLogger(__name__)

        # Data
        self.input_var = tk.StringVar()
        self.echo_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.ioloop = None  # type: asyncio.BaseEventLoop
        self.ws_client = None  # type: WebsocketClient

        # IO Loop
        self.create_io_loop()

        # View / Control
        self.create_widgets(self.window)

        # Connections
        # self.port_var.set(9999)
        self.input_var.trace("w", self.input_var_changed)
        # self.detail_var.set("")

    @property
    def status(self):
        return str(self.status_var.get())

    @status.setter
    def status(self, val):
        self.status_var.set(str(val))


    def create_io_loop(self):
        """Creates a new thread to manage an asyncio event loop specifically for IO to/from Pushbullet."""
        assert self.ioloop is None  # This should only ever be run once

        def _run(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        self.ioloop = asyncio.new_event_loop()
        self.ioloop.set_exception_handler(self._ioloop_exc_handler)
        threading.Thread(target=partial(_run, self.ioloop), name="Thread-asyncio", daemon=True).start()

    def _ioloop_exc_handler(self, loop: asyncio.BaseEventLoop, context: dict):
        print("_exc_handler", loop, context)
        pprint.pprint(context)
        if "exception" in context:
            self.status = context["exception"]

        self.status = str(context)

    def create_widgets(self, parent: tk.Frame):
        # Input
        lbl_port = tk.Label(parent, text="Type here:")
        lbl_port.grid(row=0, column=0)
        txt_port = tk.Entry(parent, textvariable=self.input_var)
        txt_port.grid(row=0, column=1)

        # Echo
        lbl_echo1 = tk.Label(parent, text="Echo here:")
        lbl_echo1.grid(row=1, column=0)
        lbl_echo2 = tk.Label(parent, textvariable=self.echo_var)
        lbl_echo2.grid(row=1,column=1)

        # Buttons
        cmd_server = tk.Button(parent, text="Connect", command=self.connect_clicked)
        cmd_server.grid(row=2, column=0)

    def input_var_changed(self, _, __, ___):
        text = self.input_var.get()
        async def _send(x):
            if self.ws_client:
                await self.ws_client.send_str(x)
        asyncio.run_coroutine_threadsafe(_send(text), self.ioloop)

    def connect_clicked(self):
        print("start")

        async def _connect():
            print("Connecting to", ECHO_WS_URL)
            async with WebsocketClient(ECHO_WS_URL, proxy=PROXY) as self.ws_client:
                print("Connected")
                async for msg in self.ws_client:
                    if msg.type == WSMsgType.TEXT:
                        text = str(msg.data)
                        self.echo_var.set(text)


        asyncio.run_coroutine_threadsafe(_connect(), self.ioloop)

if __name__ == "__main__":
    main()
