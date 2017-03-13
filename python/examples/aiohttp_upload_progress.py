#!/usr/bin/env python3
"""
Illustrates how to have upload progress using tqdm and aiohttp.

PasteBin: http://pastebin.com/ksEfNJZN
"""
import asyncio
import io
import os

import aiohttp
import time
from tqdm import tqdm

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
    loop.close()


@asyncio.coroutine
def run():
    session = aiohttp.ClientSession()

    # Upload a multipart form file normally
    # with open(__file__, "rb") as f:
    #     resp = yield from session.post("https://transfer.sh/", data={"file": f})
    # file_url = yield from resp.text()
    # print(file_url)

    # Upload a multipart form file with a progress indicator
    print()
    with tqio(__file__, slow_it_down=True) as f:
        resp = yield from session.post("https://transfer.sh/", data={"file": f})
    file_url = yield from resp.text()
    print()
    print(file_url)

    yield from session.close()


class tqio(io.BufferedReader):
    def __init__(self, file_path, slow_it_down=False):
        super().__init__(open(file_path, "rb"))
        self.t = tqdm(desc="Upload",
                      unit="bytes",
                      unit_scale=True,
                      total=os.path.getsize(file_path))

        # Artificially slow down transfer for illustration
        self.slow_it_down = slow_it_down

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def read(self, *args, **kwargs):
        if self.slow_it_down:
            chunk = super().read(64)
            self.t.update(len(chunk))
            time.sleep(.1)
            return chunk
        else:
            # Keep these three lines after getting
            # rid of slow-it-down code for illustration.
            chunk = super().read(*args, **kwargs)
            self.t.update(len(chunk))
            return chunk

    def close(self, *args, **kwargs):
        self.t.close()
        super().close()


if __name__ == '__main__':
    main()