#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example using the cancel_preexisting_call decorator, which will cancel
earlier calls to a decorated async coroutine if the earlier call has not
yet finished before the next call to the coroutine is made.
"""

import asyncio
import weakref

from handy.decorators import cancel_preexisting_call

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


@cancel_preexisting_call
async def do(x):
    print(f"Start doing {x} ...")
    await asyncio.sleep(1)
    print(f"Finished doing {x}")


@cancel_preexisting_call
async def be(x):
    print(f"Start being {x} ...")
    await asyncio.sleep(1)
    print(f"Finished being {x}")


async def run_example():
    tasks = weakref.WeakSet()
    for i in range(1, 4):
        tasks.add(asyncio.create_task(do(i)))
        tasks.add(asyncio.create_task(be(i)))
        await asyncio.sleep(0.5)
    await asyncio.gather(*tasks)
    print("See that only the final calls were completed.")


loop = asyncio.get_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(run_example())
