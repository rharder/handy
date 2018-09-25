#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Horribly dangerous.  Do not use.
"""
import asyncio
import os
import sys
import traceback
import weakref
from typing import List

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

    sys.argv.append("console")
    sys.argv.append("server")

    if "server" in sys.argv and "console" in sys.argv:
        t1 = loop.create_task(run_console())
        t2 = loop.create_task(run_cmd_server("cmd"))
        loop.run_until_complete(asyncio.gather(t1, t2))
        return

    if sys.argv[-1] == "console":
        loop.run_until_complete(run_console())

    if sys.argv[-1] == "server":
        loop.run_until_complete(run_cmd_server("cmd"))

    # loop.run_forever()


async def run_console():
    # Read console input from input() and write to pushbullet
    # Echo pushbullet from_stdout through print()
    print("Console for interacting with remote command", flush=True)
    stdout_task = None  # type: asyncio.Task
    try:
        key = asyncpushbullet.get_oauth2_key()

        async with AsyncPushbullet(key, proxy=PROXY) as pb:
            msg = {"type": "console", "status": "Console input connected to pushbullet"}
            await pb.async_push_ephemeral(msg)

            async with AsyncReadConsole() as asc:

                async def _dump_stdout():
                    try:
                        async with LiveStreamListener(pb, types=("ephemeral:console",)) as lsl:
                            async for push in lsl:
                                subpush = push.get("push")

                                for line in subpush.get("from_stdout", []):
                                    if line is None:
                                        print("Console tool reports that remote command exited.")
                                        await lsl.close()
                                    else:
                                        # print(f"stdout: {line}", flush=True)
                                        print(line, flush=True)

                                for line in subpush.get("from_stderr", []):
                                    if line is None:
                                        print("Console tool reports that remote command exited.")
                                        await lsl.close()
                                    else:
                                        # print(f"stderr: {line}", file=sys.stderr, flush=True)
                                        print(line, file=sys.stderr, flush=True)

                        # print("LSL closed (exited with block)")
                    except Exception as ex:
                        print("ERROR in _dump_stdout:", ex, file=sys.stderr, flush=True)
                        traceback.print_tb(sys.exc_info()[2])
                    finally:
                        await asc.close()

                stdout_task = asyncio.get_event_loop().create_task(_dump_stdout())

                async for line in asc:
                    if line is None:
                        asc.close()
                        break
                    else:
                        msg = {"type": "console", "for_stdin": line}
                        await pb.async_push_ephemeral(msg)


    except Exception as ex:
        print("ERROR in run_console:", ex, file=sys.stderr, flush=True)
        traceback.print_tb(sys.exc_info()[2])
    finally:
        print("Console tool closing ... ", end="", flush=True)
        if stdout_task:
            stdout_task.cancel()
        print("Closed.", flush=True)


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


async def run_cmd_server(cmd: str = None, args: List = None):
    print("Remote command server.", flush=True)
    loop = asyncio.get_event_loop()

    cmd = cmd or "cmd"
    args = args or []

    try:
        key = asyncpushbullet.get_oauth2_key()
        async with AsyncPushbullet(key, proxy=PROXY) as pb:
            # output_tasks = weakref.WeakSet()
            stdout_queue = asyncio.Queue()
            stderr_queue = asyncio.Queue()

            msg = {"type": "console", "status": "command server connected to pushbullet"}
            await pb.async_push_ephemeral(msg)
            # output_tasks.add(loop.create_task(pb.async_push_ephemeral(msg)))

            async def _output_flusher(_q, name):
                # name is from_stdout or from_stderr
                while True:
                    lines = []
                    while len(lines) < 20:
                        line = None  # type: bytes
                        try:
                            if lines:
                                # If we have something to send, wait only a moment
                                # to see if there's anything else coming.
                                # print("Waiting with timeout", name)
                                line = await asyncio.wait_for(_q.get(), timeout=0.25)
                            else:
                                # print("Waiting without timeout", name)
                                # If we have an empty queue, no need for the timeout
                                line = await _q.get()

                        except asyncio.TimeoutError:
                            # print("TE")
                            break
                            # break  # while loop for length of lines
                        else:
                            # print(f"{name}: {line}")
                            if line is None:
                                print("output flusher done!", name)
                                # return  # We're done!
                                lines.append(None)
                                break
                            else:
                                line = line.decode().rstrip()
                                lines.append(line)

                    print(f"{name} LINES:", lines)
                    if lines:
                        msg = {"type": "console", name: lines}
                        await pb.async_push_ephemeral(msg)
                        # output_tasks.add(loop.create_task(pb.async_push_ephemeral(msg)))
                        if lines[-1] is None:
                            print("Got a None. Done!", name)
                            return  # We're done

            # TODO: stderr is not exiting
            t1 = loop.create_task(_output_flusher(stdout_queue, "from_stdout"))
            t2 = loop.create_task(_output_flusher(stderr_queue, "from_stderr"))

            async with LiveStreamListener(pb, types="ephemeral:console") as lsl:

                await async_execute_command(cmd, args,
                                            provide_stdin=LiveStreamCommandListener(lsl),
                                            handle_stderr=stderr_queue.put,
                                            handle_stdout=stdout_queue.put)

                await stdout_queue.put(None)  # mark that we're done for the output flushers
                await stderr_queue.put(None)  # mark that we're done

            print("GATHERING t1 stdout...", end="", flush=True)
            await asyncio.gather(t1)
            print("GATHERING t2 stderr...")
            await asyncio.gather(t2)
            print("GATHERED.", flush=True)
            await asyncio.sleep(1)


    except Exception as ex:
        print("ERROR:", ex, file=sys.stderr, flush=True)
        traceback.print_tb(sys.exc_info()[2])

    finally:
        print("Server tool closing ... ", end="", flush=True)
        print("Closed.", flush=True)

if __name__ == "__main__":
    main()
