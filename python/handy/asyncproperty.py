#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A decorator for making a property able to be set to a
function or coroutine to be loaded lazily and awaitably
at the time it is needed.

Source: https://github.com/rharder/handy
"""

import asyncio
from functools import partial

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


class asyncproperty(property):

    # Pycharm complains about __get__ beginning with async
    # but the program executes perfectly and as expected.
    async def __get__(self, *args, **kwargs):
        val = await super().__get__(*args, **kwargs)
        check = val
        if isinstance(check, partial):
            check = check.func
        if isinstance(check, asyncio.Future) or asyncio.iscoroutine(check):
            val = await val
        elif asyncio.iscoroutinefunction(check):
            val = await val()
        elif callable(check):
            val = val()

        return val


class _Demo:

    def __init__(self):
        self._foo = None

    @asyncproperty
    async def foo(self):
        return self._foo

    @foo.setter
    def foo(self, val):
        self._foo = val


def main():
    def regular_function():
        return "Yes, regular_function got called"

    async def async_function(arg=None):
        print("(sleeping...", end="", flush=True)
        await asyncio.sleep(1)
        print(")", end="", flush=True)
        msg = "Yes, async_function got called"
        if arg is not None:
            msg += f" with argument: {arg}"
        return msg

    async def run():
        d = _Demo()

        # Pycharm complains: Property 'foo' cannot be read
        # but it executes just fine.
        x = await d.foo

        print("Setting d.foo = 42")
        d.foo = 42
        print(f"Value of d.foo: {await d.foo}")

        print("\nSetting d.foo = regular_function")
        d.foo = regular_function
        print(f"Value of d.foo: {await d.foo}")

        print("\nSetting d.foo = async_function")
        d.foo = async_function
        print(f"Value of d.foo: {await d.foo}")

        print("\nSetting d.foo = async_function()")
        d.foo = async_function()
        print(f"Value of d.foo: {await d.foo}")

        print("\nSetting d.foo = partial(async_function, 'bar')")
        d.foo = partial(async_function, 'bar')
        print(f"Value of d.foo: {await d.foo}")

    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())


if __name__ == '__main__':
    main()
