#!/usr/bin/env python3
"""
A more sophisticated Tk example using a websocket client.
"""
import asyncio
import logging
import os
import queue
import sys
import threading
import tkinter as tk
from concurrent.futures import CancelledError
from functools import partial
from typing import Callable

from aiohttp import WSMsgType  # pip install aiohttp

from handy.websocket_client import WebsocketClient

__author__ = "Robert Harder"

ECHO_WS_URL = "wss://echo.websocket.org"
PROXY = os.environ.get("https_proxy") or os.environ.get("http_proxy")


def main():
    tk_root = tk.Tk()
    _ = MainApp(tk_root)
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

        # Inter-thread communication
        self._tk_queue = queue.Queue()  # type: queue.Queue
        self._tk_after_id = None  # type: str
        self._io_scheduled_id = None  # type: asyncio.Future

        # IO Loop
        self.create_io_loop()

        # View / Control
        self.create_widgets(self.window)

        # Connections
        self.input_var.trace("w", self.input_var_changed)

        self.status = "Click connect to begin."

    @property
    def status(self):
        return str(self.status_var.get())

    @status.setter
    def status(self, val):
        if self.ioloop == asyncio.get_event_loop():
            # Set the status across event loops/threads by scheduling on tk thread
            self.tk_schedule_do(self.status_var.set, str(val))
        else:
            # Already on tk thread so set the variable directly
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
        if "message" in context:
            self.status = context["message"]
        if "exception" in context:
            self.status = context["exception"]

    def create_widgets(self, parent: tk.Frame):
        # Buttons
        cmd_server = tk.Button(parent, text="Connect", command=self.connect_clicked)
        cmd_server.grid(row=0, column=0, sticky=tk.E)

        # Input
        lbl_port = tk.Label(parent, text="Type here:")
        lbl_port.grid(row=1, column=0, sticky=tk.W)
        txt_port = tk.Entry(parent, textvariable=self.input_var, width=40)
        txt_port.grid(row=1, column=1, sticky="EW")
        tk.Grid.grid_columnconfigure(parent, 1, weight=1)

        # Echo
        lbl_echo1 = tk.Label(parent, text="Echo here:")
        lbl_echo1.grid(row=2, column=0, sticky=tk.W)
        lbl_echo2 = tk.Label(parent, textvariable=self.echo_var)
        lbl_echo2.grid(row=2, column=1, sticky=tk.W)

        # Status line
        status_line = tk.Frame(parent, borderwidth=2, relief=tk.GROOVE)
        status_line.grid(row=999, column=0, sticky="EW", columnspan=2)
        lbl_status = tk.Label(status_line, textvar=self.status_var)
        lbl_status.grid(row=0, column=1, sticky=tk.W)

    def input_var_changed(self, _, __, ___):
        self.io_schedule_send(self.input_var.get())

    def connect_clicked(self):
        # In order to schedule something on the io event loop and thread
        # create an async function and schedule it with asyncio.run_coroutine_threadsafe.
        # To go the other direction, from the io loop back to the tk thread,
        # See the example in the tk_schedule function.
        async def _connect():
            try:
                self.status = "Connecting to {}".format(ECHO_WS_URL)
                async with WebsocketClient(ECHO_WS_URL, proxy=PROXY) as self.ws_client:
                    self.status = "Connected!"
                    self.tk_schedule_do(self.input_var.set, "Start typing...")
                    async for msg in self.ws_client:
                        if msg.type == WSMsgType.TEXT:  # When the server sends us text...
                            self.status = "Received"
                            text = str(msg.data)
                            self.tk_schedule_do(self.echo_var.set, text)  # Display it in the response field
            except Exception as ex:
                print(ex.__class__.__name__, ex, file=sys.stderr)
                self.status = "{}: {}".format(ex.__class__.__name__, ex)

        asyncio.run_coroutine_threadsafe(_connect(), self.ioloop)

    def io_schedule_send(self, text):

        # Unlike the tk_schedule, what we do here is throw away previous
        # commands to send data and only send the most recent.
        # The very small sleep allows for when text is coming in fast
        # to not send every keystroke but to wait and send a larger
        # chunk of text.
        async def _send(x):
            try:
                await asyncio.sleep(0.05)
                if self.ws_client:
                    self.status = "Sending..."
                    await self.ws_client.send_str(x)
            except CancelledError:
                # Whenever we arrive here, we realize that we just saved
                # ourselves an unnecessary send/receive cycle over the network.
                pass
            except Exception as ex:
                print(ex.__class__.__name__, ex, file=sys.stderr)
                self.status = "{}: {}".format(ex.__class__.__name__, ex)

        if self._io_scheduled_id:
            self._io_scheduled_id.cancel()

        self._io_scheduled_id = asyncio.run_coroutine_threadsafe(_send(text), self.ioloop)

    def tk_schedule_do(self, cmd: Callable, *kargs, **kwargs):
        """Schedule a command to be called on the main GUI event thread."""

        def _process_tk_queue():
            while not self._tk_queue.empty():
                msg = self._tk_queue.get()  # type: Callable
                msg()

        # Put the command in a thread-safe queue and schedule the tk thread
        # to retrieve it in a few milliseconds.  The few milliseconds delay
        # helps if there's a flood of calls all at once
        self._tk_queue.put(partial(cmd, *kargs, **kwargs))
        if self._tk_after_id:
            self.window.after_cancel(self._tk_after_id)
        self._tk_after_id = self.window.after(5, _process_tk_queue)


if __name__ == "__main__":
    main()
