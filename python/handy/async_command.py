#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools for running command line processes compatibly with asyncio.
"""
import asyncio
import sys
import threading
import time
import traceback
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

    def __init__(self):
        self.queue = asyncio.Queue()
        self.loop = None  # type: asyncio.BaseEventLoop

    def __aiter__(self):
        def _thread_run():
            while True:
                try:
                    time.sleep(0.1)
                    line = input("Input (^D or EOF to quit): ").rstrip()
                    # line = input().rstrip()
                except EOFError as ex:
                    asyncio.run_coroutine_threadsafe(self.queue.put(None), self.loop)
                    break
                if line == "EOF":
                    if self.loop:
                        asyncio.run_coroutine_threadsafe(self.queue.put(None), self.loop)
                    else:
                        print("NO LOOP YET DETERMINED IN AsyncReadConsole!")
                        # is this actually possible?
                    break
                else:
                    if self.loop:
                        asyncio.run_coroutine_threadsafe(self.queue.put(line), self.loop)
                    else:
                        print("NO LOOP YET DETERMINED IN AsyncReadConsole!")

        threading.Thread(target=_thread_run, name="Thread-console_input", daemon=True).start()
        return self

    async def __anext__(self):
        self.loop = asyncio.get_event_loop()
        line = await self.queue.get()
        if line is None:
            raise StopAsyncIteration()
        else:
            return line


async def async_execute_command(cmd, args: Iterable = (), provide_stdin: AsyncIterator = None,
                                handle_stdout: Callable = None,
                                handle_stderr: Callable = None, daemon=True):
    parent_loop = asyncio.get_event_loop()
    done_flag = asyncio.Queue()

    # proc_loop = None  # type: asyncio.BaseEventLoop
    if sys.platform == 'win32':
        proc_loop = asyncio.ProactorEventLoop()
    else:
        proc_loop = asyncio.new_event_loop()  # Processes
        asyncio.get_child_watcher()  # Main loop

    def _thread_run(loop: asyncio.BaseEventLoop):
        async def __run():

            async def __call_callback(__func, *kargs, **kwargs):
                if asyncio.iscoroutinefunction(__func):
                    if parent_loop == asyncio.get_event_loop():
                        await __func(*kargs, **kwargs)
                    else:
                        asyncio.run_coroutine_threadsafe(__func(*kargs, **kwargs), parent_loop)
                else:
                    __func(*kargs, **kwargs)

            try:
                print("Launching", cmd, *args, flush=True)
                proc = await asyncio.create_subprocess_exec(
                    cmd, *args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE)

                async def __process_output(_out: asyncio.StreamReader, _output_callback: Callable):
                    # This gets called on the proc_loop
                    while True:
                        line = await _out.readline()
                        if line:
                            await __call_callback(_output_callback, line)
                        else:
                            break

                async def __receive_input(_input_provider: AsyncIterator[str]):
                    # This gets called on the parent_loop
                    async for __line in _input_provider:
                        proc.stdin.write("{}\n".format(__line).encode())
                    proc.stdin.write_eof()

                tasks = []
                if provide_stdin:
                    # tasks.append(asyncio.create_task(__receive_input(provide_stdin)))
                    asyncio.run_coroutine_threadsafe(__receive_input(provide_stdin), parent_loop)
                if handle_stdout:
                    tasks.append(asyncio.create_task(__process_output(proc.stdout, handle_stdout)))
                if handle_stderr:
                    tasks.append(asyncio.create_task(__process_output(proc.stderr, handle_stderr)))
                else:
                    tasks.append(asyncio.create_task(
                        __process_output(proc.stderr,
                                         lambda x: print(x.decode().rstrip(), file=sys.stderr, flush=True))))

                await asyncio.gather(*tasks)

            except Exception as ex:
                print(ex, file=sys.stderr, flush=True)
                traceback.print_tb(sys.exc_info()[2])

        asyncio.set_event_loop(loop)
        loop.run_until_complete(__run())
        asyncio.run_coroutine_threadsafe(done_flag.put(None), parent_loop)

    # Launch process is another thread, and wait for it to complete
    threading.Thread(target=partial(_thread_run, proc_loop), name="Thread-proc", daemon=daemon).start()
    await done_flag.get()


if __name__ == "__main__":
    main()
