#!/usr/bin/env python3
"""
Illustrates how to have upload progress using tqdm and aiohttp.

PasteBin: http://pastebin.com/ksEfNJZN
"""
import asyncio
import os

import aiohttp

from handy.tqio import tqio

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
    loop.close()


async def run():
    proxy = os.environ.get("https_proxy") or os.environ.get("http_proxy")
    session = aiohttp.ClientSession()

    # Upload a multipart form file normally
    # with open(__file__, "rb") as f:
    #     resp = yield from session.post("https://transfer.sh/", data={"file": f})
    # file_url = yield from resp.text()
    # print(file_url)

    # Upload a multipart form file with a progress indicator
    with tqio(__file__, slow_it_down=True) as f:
        resp = await session.post("https://transfer.sh/", data={"file": f}, proxy=proxy)
    file_url = await resp.text()
    print(file_url)

    await session.close()


if __name__ == '__main__':
    main()
