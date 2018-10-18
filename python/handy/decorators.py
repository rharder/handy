# -*- coding: utf-8 -*-
"""
The cancel_preexisting_call decorator will cancel
earlier calls to a decorated async coroutine if the earlier call has not
yet finished before the next call to the coroutine is made.
"""

import asyncio
import weakref
from typing import Dict

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"
__homepage__ = "https://github.com/rharder/handy"


def cancel_preexisting_call(func):
    """Decorator for async functions that will cancel the previous call
    to the function if a subsequent call is made before being completed."""

    if not hasattr(cancel_preexisting_call, "__cache__"):
        setattr(cancel_preexisting_call, "__cache__", weakref.WeakKeyDictionary())

    async def process(func, *kargs, **kwargs):
        if asyncio.iscoroutinefunction(func):
            return await func(*kargs, **kwargs)
        else:
            return func(*kargs, **kwargs)

    async def wrapper(*kargs, **kwargs):
        cache: Dict[object, weakref.WeakSet] = getattr(cancel_preexisting_call, "__cache__")
        if func not in cache:
            cache[func] = weakref.WeakSet()
        for prev_task in cache[func]:
            # print(f"Cancelling function {id(func)} {prev_task}")
            prev_task.cancel()

        task = asyncio.create_task(process(func, *kargs, **kwargs))
        cache[func].add(task)
        try:
            await asyncio.gather(task)
        except asyncio.CancelledError as ce:
            # print(f"Cancelled function {id(func)} {task} {kargs} {kwargs}")
            result = ce
        else:
            result = task.result()
            # print(f"Got result from non-cancelled function: {result}")
        finally:
            cache[func].remove(task)

        return result

    return wrapper

