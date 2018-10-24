#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Description here
"""

import asyncio
import sys

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


async def run():
    print("Put main body in this coroutine.")
    raise Exception("foo")


def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == '__main__':
    main()
