#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""
import os
import sys
import traceback

import asyncpushbullet
# from async_command import async_execute_command, AsyncReadConsole
from handy import async_command
from asyncpushbullet import AsyncPushbullet, LiveStreamListener
import asyncio

# from .async_command import async_execute_command, AsyncReadConsole

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"

PROXY = os.environ.get("https_proxy") or os.environ.get("http_proxy")


def main():
    # An example
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())


class LiveStreamCommandListener:
    def __init__(self, pb):
        self.pb = pb  # type: AsyncPushbullet
        self.lsl = None  # type: LiveStreamListener

    def __aiter__(self):
        return self

    async def __anext__(self):
        pass


async def run():
    # print("run() loop:", id(asyncio.get_event_loop()))
    try:
        key = asyncpushbullet.get_oauth2_key()
        async with AsyncPushbullet(key, proxy=PROXY) as pb:
            msg = {"type": "console", "status": "AsyncPushbullet connected"}
            await pb.async_push_ephemeral(msg)

            async def _pass_stdout_to_ephemeral(line):
                try:
                    # print("_pass_stdout_to_ephemeral() loop:", id(asyncio.get_event_loop()))
                    line = line.decode().rstrip()
                    # print("Sending", line, "...", flush=True)
                    msg = {"type": "console", "from_stdout": line}
                    await pb.async_push_ephemeral(msg)
                    # await pb.async_push_note(body=str(msg))
                    print("Sent: {}".format(line), flush=True)
                except Exception as ex:
                    print("ERROR:", ex, file=sys.stderr, flush=True)
                    traceback.print_tb(sys.exc_info()[2])

            # msg = {"type": "console", "status": "AsyncPushbullet connected"}
            # await pb.async_push_ephemeral(msg)
            # await pb.async_push_note(title="foo")

            await async_command.async_execute_command("dir", [".."],
                                                      # provide_stdin=AsyncReadConsole(),
                                                      # handle_stdout=_pass_stdout_to_ephemeral)
                                                      handle_stdout=lambda x: print("handle_stdout: {}".format(x),
                                                                                    flush=True))
            # await asyncio.sleep(2)
        #     print("Last line of 'with'")
        # print("First line after 'with'")

        # await asyncio.sleep(2)

    except Exception as ex:
        print("ERROR:", ex, file=sys.stderr, flush=True)
        traceback.print_tb(sys.exc_info()[2])


if __name__ == "__main__":
    main()
