#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uses a Python "with" construct to set up a timer with optional
messages to display before and after code executes.
"""
import sys

import time

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__date__ = "5 Dec 2016"
__license__ = "Public Domain"
__homepage__ = "https://github.com/rharder/handy"




class BeforeAndAfter:
    """
    Uses a Python "with" construct to set up a timer with optional
    messages to display before and after code executes.

    Example:

        with BeforeAndAfter(before_msg="Begin... ", after_msg="Done: {:0.2f} sec"):
            for x in range(3000):
                math.factorial(x)
    """

    def __init__(self, before_msg: str = None,
                 after_msg: str = None,
                 error_msg: str = None,
                 file=sys.stdout):

        self.__before_msg = before_msg
        self.after_msg = after_msg
        self.__file = file
        self.__error_msg = error_msg
        self.__start = None  # type: float
        self.__end = None  # type: float

    def __enter__(self):
        if self.__before_msg is not None:
            print(self.__before_msg, end='', flush=True, file=self.__file)
        self.__start = time.time()
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        self.__end = time.time()
        if ex_type is None:  # No error
            if self.after_msg is not None:
                msg = self.after_msg.format(self.elapsed)
                print(msg, file=self.__file)

    @property
    def elapsed(self):
        return self.__end - self.__start

