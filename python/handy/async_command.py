#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools for running command line processes compatibly with asyncio.
"""
import asyncio
import logging
import sys
import threading
import time
import traceback
import weakref
from functools import partial
from typing import Callable, AsyncIterator, Iterable

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


def main():
    # An example
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        async_execute_command("cmd",
                              provide_stdin=AsyncReadConsole(),
                              handle_stdout=lambda x: print(x.decode().rstrip(), flush=True)))


class AsyncReadConsole:
    """An AsyncIterator that reads from the console."""

    def __init__(self, prompt=None):
        self.queue = asyncio.Queue()  # type: asyncio.Queue
        self.loop = None  # type: asyncio.BaseEventLoop
        self.thread = None  # type: threading.Thread
        self.prompt = prompt or "Input (^D or EOF to quit): "
        self.log = logging.getLogger(__name__ + "." + self.__class__.__name__)
        self.stopping = False

    async def __aenter__(self):
        self.loop = asyncio.get_event_loop()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        # await self.close()
        # how to stop the thread?

    def __aiter__(self):
        def _thread_run():
            while not self.stopping:
                try:
                    time.sleep(0.1)
                    line = input(self.prompt).rstrip()

                except EOFError as ex:
                    asyncio.run_coroutine_threadsafe(self.queue.put(None), self.loop)
                    break
                if line == "EOF":
                    if self.loop:
                        asyncio.run_coroutine_threadsafe(self.queue.put(None), self.loop)
                    else:
                        self.log.warning("NO LOOP YET DETERMINED IN AsyncReadConsole!")
                        # is this actually possible?
                    break
                else:
                    if self.loop:
                        asyncio.run_coroutine_threadsafe(self.queue.put(line), self.loop)
                    else:
                        self.log.warning("NO LOOP YET DETERMINED IN AsyncReadConsole!")
                if line is None:
                    break
            # print("Thread is exiting")

        if self.thread is None:
            self.thread = threading.Thread(target=_thread_run, name="Thread-console_input", daemon=True)
            self.thread.start()
        return self

    async def __anext__(self):
        self.loop = asyncio.get_event_loop()
        # print("GETTING __anext__ LINE")
        line = await self.readline()
        # print("__anext__ RETRIEVED ", line)
        if line is None:
            # print("RAISING STOP ASYNC")
            raise StopAsyncIteration()
        else:
            return line

    async def readline(self):
        return await self.queue.get()

    async def close(self):
        self.stopping = True
        # print(self, "close called")
        # asyncio.run_coroutine_threadsafe(self.queue.put(None), self.loop)
        await self.queue.put(None)


async def async_execute_command(cmd, args: Iterable = (),
                                provide_stdin: AsyncIterator = None,
                                handle_stdout: Callable = None,
                                handle_stderr: Callable = None, daemon=True):
    parent_loop = asyncio.get_event_loop()
    parent_loop_tasks = weakref.WeakSet()
    done_flag = asyncio.Queue()
    callback_queue = asyncio.Queue()

    async def _monitor_callback_queue():
        # await asyncio.sleep(1)
        while True:
            try:
                x = await callback_queue.get()
                if x is None:
                    break
                check = x.func if isinstance(x, partial) else x
                if asyncio.iscoroutinefunction(check):
                    await x()
                else:
                    x()
            except Exception as ex:
                print("Error in callback:", ex.__class__.__name__, ex, file=sys.stderr, flush=True)
                traceback.print_tb(sys.exc_info()[2])

    parent_loop_tasks.add(asyncio.create_task(_monitor_callback_queue()))

    if sys.platform == 'win32':
        proc_loop = asyncio.ProactorEventLoop()
    else:
        proc_loop = asyncio.new_event_loop()  # Processes
        asyncio.get_child_watcher()  # Main loop

    def _thread_run(loop: asyncio.BaseEventLoop):
        # Running on thread that will host proc_loop

        async def __run():
            # Running within proc_loop

            try:
                print("Server is launching", cmd, *args, flush=True)
                proc = await asyncio.create_subprocess_exec(
                    cmd, *args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE)

                async def __process_output(_out: asyncio.StreamReader, _output_callback: Callable):
                    # Runs within proc_loop
                    while True:
                        line = await _out.readline()
                        if line:
                            part = partial(_output_callback, line)
                            asyncio.run_coroutine_threadsafe(callback_queue.put(part), parent_loop)
                        else:
                            break

                async def __receive_input(_input_provider: AsyncIterator[str]):
                    # Runs in parent_loop
                    async for __line in _input_provider:
                        proc.stdin.write("{}\n".format(__line).encode())
                    proc.stdin.write_eof()

                tasks = []
                if provide_stdin:
                    asyncio.run_coroutine_threadsafe(__receive_input(provide_stdin), parent_loop)
                if handle_stdout:
                    tasks.append(asyncio.create_task(__process_output(proc.stdout, handle_stdout)))
                if handle_stderr:
                    tasks.append(asyncio.create_task(__process_output(proc.stderr, handle_stderr)))

                await asyncio.gather(*tasks)

            except Exception as ex:
                print(ex, file=sys.stderr, flush=True)
                traceback.print_tb(sys.exc_info()[2])

        asyncio.set_event_loop(loop)
        loop.run_until_complete(__run())
        asyncio.run_coroutine_threadsafe(done_flag.put(None), parent_loop)

    # Launch process is another thread, and wait for it to complete
    threading.Thread(target=partial(_thread_run, proc_loop), name="Thread-proc", daemon=daemon).start()
    await done_flag.get()  # Waiting for proc_loop thread to finish
    await callback_queue.put(None)  # Signal that no more callbacks will be called
    await asyncio.gather(*parent_loop_tasks)  # Wait for all callbacks to finish


if __name__ == "__main__":
    main()
