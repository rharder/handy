#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helpful functions for making multiple attempts at functions that may raise Exceptions.
"""

import asyncio
import sys
import time

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"
__homepage__ = "https://github.com/rharder/handy"


def retry(func, max_attempts=3, retry_interval=10, default=None, exception_handler=None):
    """Reusable function for making multiple attempts at something that could raise an Exception."""
    result = default

    for attempt_num in range(1, max_attempts + 1):
        try:
            result = func()
        except Exception as ex:
            if exception_handler is not None:
                exception_handler(ex)

            if attempt_num < max_attempts:
                delay = attempt_num * retry_interval
                print(f"Exception on attempt {attempt_num} of {max_attempts}. Retrying in {delay} seconds. ({ex})",
                      file=sys.stderr)
                time.sleep(delay)
            else:
                print(f"Exception on attempt {attempt_num} of {max_attempts}. Returning default value. ({ex})",
                      file=sys.stderr)
        else:
            break

    return result


async def async_retry(func, max_attempts=3, retry_interval=10, default=None, exception_handler=None):
    """Reusable function for making multiple attempts at something that could raise an Exception."""
    result = default

    for attempt_num in range(1, max_attempts + 1):
        try:
            result = await func()
        except Exception as ex:

            if exception_handler is not None:
                if asyncio.iscoroutinefunction(exception_handler):
                    await exception_handler(ex)
                elif callable(exception_handler):
                    exception_handler(ex)

            if attempt_num < max_attempts:
                delay = attempt_num * retry_interval
                print(f"Exception on attempt {attempt_num} of {max_attempts}. Retrying in {delay} seconds. ({ex})",
                      file=sys.stderr)
                await asyncio.sleep(delay)
            else:
                print(f"Exception on attempt {attempt_num} of {max_attempts}. Returning default value. ({ex})",
                      file=sys.stderr)
        else:
            break

    return result
