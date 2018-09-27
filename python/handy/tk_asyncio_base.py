#!/usr/bin/env python3
"""
A base class for Tk apps that will use asyncio.
"""
import asyncio
import os
import pprint
import queue
import sys
import threading
import time
import tkinter as tk
import traceback
from contextlib import suppress
from functools import partial
from typing import Callable, Union, Coroutine

import aiohttp

__author__ = "Robert Harder"


def main():
    tk_root = tk.Tk()
    _ = ExampleApp(tk_root)
    tk_root.mainloop()


class TkAsyncioBaseApp:
    """


        def show_error(*args):
            a = traceback.format_exception(*args)
            print(a)
        self.root.report_callback_exception = show_error


    """

    def __init__(self, base: tk.Misc):
        self.__tk_base: tk.Misc = base

        # Inter-thread communication
        self._ioloop: asyncio.BaseEventLoop = None
        self.__tk_queue: queue.Queue = queue.Queue()
        self.__tk_after_id: str = None
        # self.__io_queue: asyncio.Queue = None

        # IO Loop
        self.__create_io_loop()

    def __create_io_loop(self):
        """Creates a new thread to manage an asyncio event loop."""
        if self._ioloop is not None:
            raise Exception("An IO loop is already running.")

        _ready = threading.Event()  # Don't leave this function until thread is ready

        def _thread_run(loop: asyncio.BaseEventLoop):
            asyncio.set_event_loop(loop)
            loop.call_soon_threadsafe(_ready.set)
            # async def _prep():
            #     self.__io_queue = asyncio.Queue()
            # loop.call_soon_threadsafe(_prep())
            loop.run_forever()

        self._ioloop = asyncio.new_event_loop()
        self._ioloop.set_exception_handler(self.ioloop_exception_happened)
        threading.Thread(target=partial(_thread_run, self._ioloop), name="Thread-asyncio", daemon=True).start()
        _ready.wait()

    def ioloop_exception_happened(self, loop: asyncio.BaseEventLoop, context: dict):
        print("TkAsyncioBaseApp.ioloop_exception_happened called.  Override this function in your app.",
              file=sys.stderr, flush=True)
        print(pprint.pformat(context), file=sys.stderr, flush=True)
        traceback.print_tb(sys.exc_info()[2])

    def tkloop_exception_happened(self, extype, ex, tb, func):
        """Called when there is an unhandled exception in a job that was
        scheduled on the tk event loop.

        The arguments are the three standard sys.exc_info() arguments
        plus the function that was called as a scheduled job and subsequently
        raised the Exception.

        :param extype: the exception type
        :param ex: the Exception object that was raised
        :param tb: the traceback associated with the exception
        :param func: the scheduled function that caused the trouble
        """
        print("TkAsyncioBaseApp.tkloop_exception_happened was called.  Override this function in your app.",
              file=sys.stderr, flush=True)
        print("Exception:", extype, ex, func, file=sys.stderr, flush=True)
        traceback.print_tb(tb)

    def io(self, func: Union[Coroutine, Callable], *kargs, **kwargs) -> Union[asyncio.Future, asyncio.Handle]:
        """
        Schedule a coroutine or regular function to be called on the io event loop.

        self.io(some_coroutine())
        self.io(some_func, "some arg")

        The positional *kargs and named **kwargs arguments only apply when
        a non-coroutine function is passed such as:

            self.io(print, "hello world", file=sys.stderr)

        Returns a Future (for coroutines) or Handle (for regular functions) that can
        be used to cancel or otherwise inspect the scheduled job.

        This is threadsafe.

        :param func: the coroutine or function
        :param kargs: optional positional arguments for the function
        :param kwargs: optional named arguments for the function
        :return:
        """
        q = queue.Queue()

        async def _run():
            # Wrap everything in an async def because we need to use
            # create_task or call_soon in order for the exception
            # handler to be called when there's an exception.
            await asyncio.sleep(0.02)
            if asyncio.iscoroutine(func):
                # print("ADDING TASK", func, flush=True)
                task = asyncio.get_event_loop().create_task(func)
                # print("ADDED TASK", task, flush=True)
                q.put(task)
                # print("PUT TASK", task, flush=True)
            else:
                # print("FUNCTION", flush=True)
                f = partial(func, *kargs, **kwargs)
                handle = asyncio.get_event_loop().call_soon(f)
                q.put(handle)

        print("run_coroutine_threadsafe...", end="", flush=True)
        asyncio.run_coroutine_threadsafe(_run(), self._ioloop)
        print("run_coroutine_threadsafe DONE", flush=True)
        time.sleep(0.15)
        print("QUEUE SIZE:", q.qsize(), flush=True)
        x = q.get()
        print("RETRIEVED FROM QUEUE", x, flush=True)
        return x

    # def __io_flush_queue(self):
    #     """Used internally to actually flush the io task queue."""
    #
    #     # print("FLUSHING", flush=True)
    #     while True:
    #         # print(".", end="", flush=True)
    #         try:
    #             func = self.__tk_queue.get(block=False)
    #             func = await self.__io_queue.get()
    #         except queue.Empty:
    #             break  # empty queue - we're done!
    #         else:
    #             # noinspection PyBroadException
    #             try:
    #                 func()
    #             except Exception as ex:
    #                 self.tkloop_exception_happened(*sys.exc_info(), func)
    #     # print("DONE FLUSHING", flush=True)

    def tk(self, func: Callable, *kargs, **kwargs):
        """
        Schedule a function to be called on the Tk GUI event loop.

        This is threadsafe.

        :param func: The function to call
        :param kargs: optional positional arguments
        :param kwargs: optional named arguments
        :return:
        """

        # Put the command in a thread-safe queue and schedule the tk thread
        # to retrieve it in a few milliseconds.  The few milliseconds delay
        # helps if there's a flood of calls all at once.
        self.__tk_queue.put(partial(func, *kargs, **kwargs))

        # if self.__tk_after_id:
        #     self.__tk_base.after_cancel(self.__tk_after_id)

        self.__tk_after_id = self.__tk_base.after(25, self.__tk_flush_queue)

    def tk_flush_queue(self):
        """Executes all the scheduled tasks in the tk event loop.

        This is called automatically within a few milliseconds after the
        last call to xxx.tk(), but if a flood of calls comes in to xxx.tk()
        then you might find it necessary to force a "flush" of the scheduled
        tasks to help with the user interface.

        This is threadsafe.
        """
        self.__tk_base.after(0, self.__tk_flush_queue)

    def __tk_flush_queue(self):
        """Used internally to actually flush the tk task queue."""

        # print("FLUSHING", flush=True)
        while True:
            # print(".", end="", flush=True)
            try:
                func = self.__tk_queue.get(block=False)
            except queue.Empty:
                break  # empty queue - we're done!
            else:
                # noinspection PyBroadException
                try:
                    func()
                except Exception as ex:
                    self.tkloop_exception_happened(*sys.exc_info(), func)
        # print("DONE FLUSHING", flush=True)


class ExampleApp(TkAsyncioBaseApp):
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

        # async def amess_around():
        #     print("AMessing around...", flush=True)
        #     raise Exception("Uh oh! in async mess around")
        #     await asyncio.sleep(1)
        #     print("Done amessing around", flush=True)
        #
        # x = self.io(amess_around())
        # # x.cancel()

        # def mess_around():
        #     print("Messing around...", flush=True)
        #     time.sleep(1)
        #     raise Exception("Uh oh! in sync mess around")
        #     print("Done messing around.", flush=True)
        #
        # x = self.tk(mess_around)
        # # x.cancel()

    @property
    def status(self):
        return str(self.status_var.get())

    @status.setter
    def status(self, val):
        # Works from any thread
        self.tk(self.status_var.set, str(val))

    def ioloop_exception_happened(self, loop: asyncio.BaseEventLoop, context: dict):
        # super().ioloop_exception_happened(loop, context)
        if "message" in context:
            self.status = context["message"]
        if "exception" in context:
            self.status = context["exception"]

    def tkloop_exception_happened(self, extype, ex, tb, func):
        # super().tkloop_exception_happened(extype, ex, tb, func)
        self.status = f"Exception: {ex}"

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
            async with aiohttp.ClientSession() as session:
                async with session.get(self.URL, proxy=self.PROXY) as resp:  # type: aiohttp.ClientResponse
                    text = await resp.text()
                    self.status = text  # Status line
                    self.tk(self.root.title, text)  # Window Title, for kicks

        self.io(_connect())


if __name__ == "__main__":
    main()
