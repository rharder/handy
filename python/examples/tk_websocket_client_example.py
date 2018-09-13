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
import traceback
from concurrent.futures import CancelledError
from functools import partial
from typing import Callable

from aiohttp import WSMsgType  # pip install aiohttp

from handy.websocket_client import WebsocketClient

__author__ = "Robert Harder"

ECHO_WS_URL = "wss://echo.websocket.org"
PROXY = os.environ.get("https_proxy") or os.environ.get("http_proxy")
# ECHO_WS_URL = "ws://localhost:9990/cap"
# PROXY = None

# logging.basicConfig(level=logging.DEBUG)
# logging.basicConfig(level=logging.INFO)


# PROXY = None

def main():
    tk_root = tk.Tk()
    _ = MainApp(tk_root)
    tk_root.mainloop()


class MainApp:
    def __init__(self, root):
        self.window = root
        root.title("Websocket Example")
        self.log = logging.getLogger(__name__)
        # self.log = logging.getLogger("{file}.{klass}:{id}".format(file=__name__, klass=self.__class__.__name__, id=id(self)))

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
        self.txt_input = None  # type: tk.Entry
        # self.btn_connect = None  # type: tk.Button
        self.create_widgets(self.window)

        # Connections
        self.input_var.trace("w", self.input_var_changed)

        self.status = "Click connect to begin."
        self.connect_clicked()

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
        print("_exc_handler", loop, context, file=sys.stderr, flush=True)
        if "message" in context:
            self.status = context["message"]
        if "exception" in context:
            self.status = context["exception"]

    def create_widgets(self, parent: tk.Frame):
        # Buttons
        btn_connect = tk.Button(parent, text="Connect", command=self.connect_clicked)
        btn_connect.grid(row=0, column=0, sticky=tk.E)

        # Input
        lbl_type_here = tk.Label(parent, text="Type here:")
        lbl_type_here.grid(row=1, column=0, sticky=tk.W)
        self.txt_input = tk.Entry(parent, textvariable=self.input_var, width=40)
        self.txt_input.grid(row=1, column=1, sticky="EW")
        self.txt_input.configure(state=tk.DISABLED)
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

    def connect_clicked(self):  # , btn:tk.Button):
        # In order to schedule something on the io event loop and thread
        # create an async function and schedule it with asyncio.run_coroutine_threadsafe.
        # To go the other direction, from the io loop back to the tk thread,
        # See the example in the tk_schedule_do function.
        async def _connect():
            try:
                if self.ws_client:
                    self.status = "Disconnecting..."
                    await self.ws_client.close()
                    self.ws_client = None

                self.status = "Connecting to {}".format(ECHO_WS_URL)
                async with WebsocketClient(ECHO_WS_URL, proxy=PROXY) as self.ws_client:
                    self.status = "Connected!  Start typing..."
                    self.tk_schedule_do(self.txt_input.configure, state=tk.NORMAL)
                    self.tk_schedule_do(self.txt_input.focus_set)

                    # # self.ws_client.flush_incoming_threadsafe(timeout=None)
                    # await asyncio.sleep(0.1)
                    # for i in range(10):
                    #     await self.ws_client.send_str("i={}".format(i))
                    # await self.ws_client.send_str("one")
                    # await self.ws_client.send_str("two")
                    # await self.ws_client.send_str("Should have been flushed")
                    # print("Flushing...")
                    # # await asyncio.sleep(0.25)
                    # await self.ws_client.flush_incoming(timeout=0.25)
                    # print("Flushed.")

                    async for msg in self.ws_client:
                        if msg.type == WSMsgType.TEXT:  # When the server sends us text...
                            text = str(msg.data)
                            self.log.debug("Rcvd {}".format(text))
                            self.status = "Received {}".format(text)
                            self.tk_schedule_do(self.echo_var.set, text)  # Display it in the response field


            except Exception as ex:
                print(ex.__class__.__name__, ex, file=sys.stderr)
                self.status = "{}: {}".format(ex.__class__.__name__, ex)
                # traceback.print_tb(sys.exc_info()[2])
            else:
                self.status = "Disconnected."

        asyncio.run_coroutine_threadsafe(_connect(), self.ioloop)

    def io_schedule_send(self, text):
        """Schedules data to be sent on the io loop.

        Unlike the tk_schedule, what we do here is throw away previous
        commands to send data and only send the most recent.
        The very small sleep allows for when text is coming in fast
        to not send every keystroke but to wait and send a larger
        chunk of text.
        """

        async def _send(x):
            try:
                await asyncio.sleep(0.1)
                if self.ws_client:
                    self.status = "Sending {}".format(x)
                    self.log.debug("Sending {}".format(x))
                    await self.ws_client.send_str(x)
                    self.status = "Sent {}".format(x)
                    self.log.debug("Sent {}".format(x))

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
        """Schedule a command to be called on the main GUI event thread.

        How important is it to schedule tk events on the tk thread?
        Not very, in my findings.  Tk has not given me grief when I manipulate
        it from the io loop, for example.  However, when making significant
        changes to the GUI, such as adding a large number of items to a Listbox,
        the io loop occasionally spits out weird errors about functions taking
        too long, which I tracked back to the GUI calls blocking until they're done.
        Asyncio doesn't seem to like that.

        Still, to have the best-behaved program, this example shows how to schedule
        events to happen on the GUI thread where they belong.
        """

        def _process_tk_queue():
            # print("Queue has {} items to process.".format(self._tk_queue.qsize()))
            # count = 0
            while not self._tk_queue.empty():
                msg = self._tk_queue.get()  # type: Callable
                msg()
                # count += 1
            # print("Processed {} items.".format(count))

        # Put the command in a thread-safe queue and schedule the tk thread
        # to retrieve it in a few milliseconds.  The few milliseconds delay
        # helps if there's a flood of calls all at once.
        self._tk_queue.put(partial(cmd, *kargs, **kwargs))
        if self._tk_after_id:
            self.window.after_cancel(self._tk_after_id)
        self._tk_after_id = self.window.after(5, _process_tk_queue)


if __name__ == "__main__":
    main()
