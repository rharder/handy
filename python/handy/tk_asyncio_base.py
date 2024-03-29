#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A base class for Tk apps that will use asyncio.
"""
import asyncio
import queue
import sys
import threading
import tkinter as tk
import traceback
import types
from concurrent.futures import CancelledError
from functools import partial
from typing import Callable, Union, Coroutine

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"
__homepage__ = "https://github.com/rharder/handy"


class TkAsyncioBaseApp:
    """
    A base app (or object you can instantiate) to help manage asyncio loops and
    tkinter event loop and executing tasks across their borders.

    For example if you are responding to a button click you might want to fire off
    some communication that uses asyncio functions.  That might look like this:

    class MyGuiApp(TkAsyncioBaseApp):
        def __init__(self, tkroot):
            super().__init__(tkroot)
            ...

        def my_button_clicked(self):
            self.my_button.configure(state=tk.DISABLED)
            self.on_async(connect())  # Launch a coroutine on a thread managing an asyncio loop

        async def connect(self):
            await some_connection_stuff()
            self.on_tk(self.my_button.configure, state=tk.NORMAL)  # Run GUI commands on main thread

    """

    def __init__(self, base: tk.Misc):
        self.__tk_base: tk.Misc = base

        # Inter-thread communication
        self._ioloop: asyncio.BaseEventLoop = None
        self.__tk_queue: queue.Queue = queue.Queue()  # Functions to call on tk loop
        self.__tk_after_ids: queue.Queue = queue.Queue()  # Requests to process tk queue

        # IO Loop
        self.__create_async_loop()

    def __create_async_loop(self):
        """Creates a new thread to manage an asyncio event loop."""
        if self._ioloop is not None:
            raise Exception("An IO loop is already running.")

        _ready = threading.Event()  # Don't leave this function until thread is ready

        def _thread_run(loop: asyncio.BaseEventLoop):
            asyncio.set_event_loop(loop)
            loop.call_soon_threadsafe(_ready.set)
            loop.run_forever()

        self._ioloop: asyncio.BaseEventLoop = asyncio.new_event_loop()
        threading.Thread(target=partial(_thread_run, self._ioloop), name="Thread-asyncio", daemon=True).start()
        _ready.wait()

    async def ioloop_exception_happened(self, extype: type, ex: Exception, tb: types.TracebackType, coro: Coroutine):
        """Called when there is an unhandled exception in a job that was
        scheduled on the io event loop.

        The arguments are the three standard sys.exc_info() arguments
        plus the function that was called as a scheduled job and subsequently
        raised the Exception.

        :param extype: the exception type
        :param ex: the Exception object that was raised
        :param tb: the traceback associated with the exception
        :param coro: the scheduled function that caused the trouble
        """
        pass
        print("TkAsyncioBaseApp.ioloop_exception_happened called.  Override this function in your app.",
              file=sys.stderr, flush=True)
        print(f"coro: {coro}", file=sys.stderr, flush=True)
        traceback.print_tb(tb)

    def tkloop_exception_happened(self, extype: type, ex: Exception, tb: types.TracebackType, func: partial):
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
        pass
        print("TkAsyncioBaseApp.tkloop_exception_happened was called.  Override this function in your app.",
              file=sys.stderr, flush=True)
        print("Exception:", extype, ex, func, file=sys.stderr, flush=True)
        print(f"func: {func}", file=sys.stderr, flush=True)
        print(f"kargs: {func.args}", file=sys.stderr, flush=True)
        print(f"kwargs: {func.keywords}", file=sys.stderr, flush=True)
        traceback.print_tb(tb)

    def on_async(self,
                 func: Union[Coroutine, Callable],
                 callback: Callable = None) -> Union[asyncio.Future, asyncio.Handle]:
        """
        Schedule a coroutine or regular function to be called on the io event loop.

        self.on_async(some_coroutine())
        self.on_async(some_func, "some arg")

        The positional *kargs and named **kwargs arguments only apply when
        a non-coroutine function is passed such as:

            self.on_async(print, "hello world", file=sys.stderr)

        Returns a Future (for coroutines) or Handle (for regular functions) that can
        be used to cancel or otherwise inspect the scheduled job.

        This is threadsafe.

        :param func: the coroutine or function
        :param kargs: optional positional arguments for the function
        :param kwargs: optional named arguments for the function
        :return:
        """

        async def _coro_run():
            # noinspection PyBroadException
            try:
                await func
            except Exception:
                await self.ioloop_exception_happened(*sys.exc_info(), func)

        def _func_run():
            # noinspection PyBroadException
            try:
                func()
            except Exception:
                self.tkloop_exception_happened(*sys.exc_info(), func)

        if asyncio.iscoroutine(func):
            fut = asyncio.run_coroutine_threadsafe(_coro_run(), self._ioloop)
        else:
            fut = self._ioloop.call_soon_threadsafe(_func_run)

        # Optional callback on the original GUI event thread
        if callback:
            fut.add_done_callback(lambda f: self.on_tk(callback, f.result()))

        return fut

    def on_thread(self, func: Callable, callback: Callable = None):
        """Run a non-async function on another thread and make an optional callback
        to the event thread when complete. The results returned from the
        first function (on the other thread) will be passed as the argument to the callback.

        Example:

            def long_task():
                # This is run on another thread (but not async)
                results = load_some_big_file_from_disk_or_something()
                return results

            def cleanup(file_contents)
                # This is run on GUI event thread
                some_tk_widget.configure(text=file_contents)

            self.on_thread(func=long_task, callback=cleanup)

        """

        def _func_run():
            # noinspection PyBroadException
            try:
                result = func()
                if callback:
                    self.on_tk(callback, result)
            except Exception:
                # Maybe the following needs to change - this is not running on the tk loop
                self.tkloop_exception_happened(*sys.exc_info(), func)

        threading.Thread(target=_func_run).start()

    def on_tk(self, func: Callable, *kargs, **kwargs):
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

        x = TkTask(func, *kargs, **kwargs)
        self.__tk_queue.put(x)

        # Now throw away old requests to process the tk queue
        while True:
            try:
                old_scheduled_timer = self.__tk_after_ids.get(block=False)
                self.__tk_base.after_cancel(old_scheduled_timer)
            except queue.Empty:
                break
        self.__tk_after_ids.put(self.__tk_base.after(5, self._tk_process_queue))

        return x

    def _tk_process_queue(self):
        """Used internally to actually process the tk task queue."""
        while True:
            try:
                x: TkTask = self.__tk_queue.get(block=False)
            except queue.Empty:
                break  # empty queue - we're done!
            else:
                # noinspection PyBroadException
                try:
                    x.run()  # Will skip if task is cancelled
                except Exception:
                    extype, ex, tb = sys.exc_info()
                    self.tkloop_exception_happened(extype, ex, tb, x.job())


class TkTask:
    """A task-like object scheduled from, presumably, an asyncio loop or other thread."""

    def __init__(self, func: Callable, *kargs, **kwargs):
        self._job: partial = partial(func, *kargs, **kwargs)
        self._cancelled: bool = False
        self._result = None
        self._result_ready: threading.Event = threading.Event()

        self._run_has_been_attempted: bool = False
        self._exception: Exception = None

        self._host_loop: asyncio.BaseEventLoop = None
        self._host_loop_result_ready: asyncio.Event = None
        try:
            self._host_loop = asyncio.get_event_loop()
            self._host_loop_result_ready: asyncio.Event = asyncio.Event()
        except RuntimeError:
            # Whichever thread called this isn't using asyncio--that's OK
            pass

    def run(self):
        if self._run_has_been_attempted:
            raise RuntimeError(f"Job has already been run: {self._job}")

        elif not self.cancelled():
            try:
                x = self._job()
            except Exception as ex:
                self._exception = ex
                raise ex
            else:
                self._set_result(x)
            finally:
                self._run_has_been_attempted = True

    def _set_result(self, val):
        self._result = val
        self._result_ready.set()
        if self._host_loop:
            self._host_loop.call_soon_threadsafe(self._host_loop_result_ready.set)

    def cancel(self):
        self._cancelled = True

    def cancelled(self) -> bool:
        return self._cancelled

    def done(self) -> bool:
        return self._run_has_been_attempted or self._cancelled

    def job(self) -> partial:
        return self._job

    async def async_result(self, timeout=None):
        """
        Await a result without blocking an asyncio loop.

        Raises concurrent.futures.TimeoutError if times out.
        :param timeout:
        :return:
        """
        if timeout is None:
            await self._host_loop_result_ready.wait()
        else:
            await asyncio.wait_for(self._host_loop_result_ready.wait(), timeout=timeout)

        return self.result()

    def result(self, timeout=None):
        if self._exception is not None:
            raise self._exception
        elif self._cancelled:
            raise CancelledError()
        else:
            if self._result_ready.wait(timeout):
                return self._result
            else:
                raise TimeoutError(f"Timeout of {timeout} seconds exceeded.")
