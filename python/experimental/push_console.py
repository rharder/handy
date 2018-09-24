#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Horribly dangerous.  Do not use.
"""
import asyncio
import os
import sys
import traceback

import asyncpushbullet
# from async_command import async_execute_command, AsyncReadConsole
from asyncpushbullet import AsyncPushbullet, LiveStreamListener

# from .async_command import async_execute_command, AsyncReadConsole
from handy.async_command import AsyncReadConsole, async_execute_command

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"

PROXY = os.environ.get("https_proxy") or os.environ.get("http_proxy")


def main():
    # An example
    loop = asyncio.get_event_loop()

    loop.create_task(run_console())
    loop.run_until_complete(run_cmd_server())

    loop.run_forever()


async def run_console():
    # Read console input from input() and write to pushbullet
    # Echo pushbullet from_stdout through print()
    print("Console for interacting with remote command", flush=True)
    try:
        key = asyncpushbullet.get_oauth2_key()
        async with AsyncPushbullet(key, proxy=PROXY) as pb:
            msg = {"type": "console", "status": "Console input connected to pushbullet"}
            await pb.async_push_ephemeral(msg)

            async def _dump_stdout():
                try:
                    async with LiveStreamListener(pb, types=("ephemeral:console",)) as lsl:
                        async for push in lsl:
                            subpush = push.get("push")
                            for line in subpush.get("from_stdout", []):
                                print(f"STDOUT: {line}", flush=True)
                            for line in subpush.get("from_stderr", []):
                                print(f"STDERR: {line}", file=sys.stderr, flush=True)
                except Exception as ex:
                    print("ERROR:", ex, file=sys.stderr, flush=True)
                    traceback.print_tb(sys.exc_info()[2])

            async def _feed_stdin():
                try:
                    async for line in AsyncReadConsole():
                        msg = {"type": "console", "for_stdin": line}
                        # print("PUSHING", msg)
                        await pb.async_push_ephemeral(msg)
                except Exception as ex:
                    print("ERROR:", ex, file=sys.stderr, flush=True)
                    traceback.print_tb(sys.exc_info()[2])

        asyncio.get_event_loop().create_task(_dump_stdout())
        asyncio.get_event_loop().create_task(_feed_stdin())

    except Exception as ex:
        print("ERROR:", ex, file=sys.stderr, flush=True)
        traceback.print_tb(sys.exc_info()[2])


class LiveStreamCommandListener:
    def __init__(self, lsl):
        self.lsl = lsl  # type: LiveStreamListener

    def __aiter__(self):
        # self.lsl = LiveStreamListener(self.pb, types=("ephemeral:console"))
        # return self.lsl.__aiter__()
        return self

    async def __anext__(self):
        line = None
        while line is None:
            msg = await self.lsl.next_push()
            if "for_stdin" in msg.get("push", {}):
                line = msg.get("push").get("for_stdin")
        print(f"Received command: {line}")
        return line


async def run_cmd_server():
    print("Remote command server.", flush=True)

    stdout_queue = asyncio.Queue()
    stderr_queue = asyncio.Queue()

    try:
        key = asyncpushbullet.get_oauth2_key()
        async with AsyncPushbullet(key, proxy=PROXY) as pb:
            msg = {"type": "console", "status": "command server connected to pushbullet"}
            await pb.async_push_ephemeral(msg)

            async with LiveStreamListener(pb, types="ephemeral:console") as lsl:

                async def _output_flusher(_q, name):
                    # name is from_stdout or from_stderr
                    while True:
                        lines = []
                        while len(lines) < 20:
                            try:
                                if lines:
                                    # If we have something to send, wait only a moment
                                    # to see if there's anything else coming.
                                    line = await asyncio.wait_for(_q.get(), timeout=0.1)
                                else:
                                    # If we have an empty queue, no need for the timeout
                                    line = await _q.get()

                            except asyncio.TimeoutError:
                                break  # while loop for length of lines
                            else:
                                if line is None:
                                    return  # We're done!
                                line = line.decode().rstrip()
                                lines.append(line)

                        if lines:
                            msg = {"type": "console", name: lines}
                            await pb.async_push_ephemeral(msg)

                asyncio.get_event_loop().create_task(_output_flusher(stdout_queue, "from_stdout"))
                asyncio.get_event_loop().create_task(_output_flusher(stderr_queue, "from_stderr"))

                await async_execute_command("cmd", [".."],
                                            provide_stdin=LiveStreamCommandListener(lsl),
                                            handle_stderr=stderr_queue.put,
                                            handle_stdout=stdout_queue.put)

                await stdout_queue.put(None)  # mark that we're done


    except Exception as ex:
        print("ERROR:", ex, file=sys.stderr, flush=True)
        traceback.print_tb(sys.exc_info()[2])


if __name__ == "__main__":
    main()
