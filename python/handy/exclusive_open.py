#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Synchronize on a file lock across processes.

From https://codereview.stackexchange.com/questions/150139/thread-safe-file-operation
"""
import asyncio
import os
import random
import sys
import tempfile
import traceback
from contextlib import contextmanager
from datetime import datetime, timedelta
from time import sleep

__author__ = "stackexchange"


def example():
    filename = f"{__file__}_test.txt"

    async def writer(name):
        asyncio.get_event_loop().set_debug(True)
        while True:
            try:
                with exclusive_open(filename, "a", foo=name) as f:
                    line = f"{datetime.now()} :: hello from {name}"
                    print(line, file=f)
                    # await asyncio.sleep(random.random() * 0.2)

                await asyncio.sleep(random.random() * 0.1)

            except Exception as ex:
                print(ex)
                traceback.print_tb(sys.exc_info()[2])

    async def run():
        tasks = []
        tasks.append(asyncio.get_event_loop().create_task(writer("Alice")))
        tasks.append(asyncio.get_event_loop().create_task(writer("Bob")))
        await asyncio.gather(*tasks)

    asyncio.get_event_loop().run_until_complete(run())


@contextmanager
def exclusive_open(filename, *args, timeout=3, retry_time=0.05, **kwargs):
    """Open a file with exclusive access across multiple processes.
    Requires write access to the directory containing the file.

    Arguments are the same as the built-in open, except for two
    additional keyword arguments:

    timeout -- Seconds to wait before giving up (or None to retry indefinitely).
    retry_time -- Seconds to wait before retrying the lock.

    Returns a context manager that closes the file and releases the lock.

    From https://codereview.stackexchange.com/questions/150139/thread-safe-file-operation
    """
    _name = kwargs["foo"]
    del kwargs["foo"]
    lockfile = filename + ".lock"
    if timeout is not None:
        deadline = datetime.now() + timedelta(seconds=timeout)
    else:
        deadline = None
    while True:
        try:
            fd = os.open(lockfile, os.O_CREAT|os.O_EXCL)
            break
        except (FileExistsError, PermissionError):
            if timeout is not None and datetime.now() >= deadline:
                raise
            print(f"Z_{_name}_Z", end=" ", flush=True)
            sleep(retry_time)
    try:
        print(_name, "opening", filename)
        with open(filename, *args, **kwargs) as f:
            yield f
    finally:
        try:
            os.close(fd)
        finally:
            os.unlink(lockfile)


if __name__ == '__main__':
    example()
