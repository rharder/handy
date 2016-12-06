#!/usr/bin/env python3
"""

"""
import sys

import time

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__date__ = "5 Dec 2016"


class BeforeAndAfter:
    """
    Handy context manager for printing a line that has some processing before finishing.

    Example:
    Performing long calculation...

    and a moment later:

    Performing long calculation...Done.
    """

    def __init__(self, before_msg: str = None,
                 after_msg: str = None,
                 error_msg: str = None,# test: bool = True, timer: bool = False,
                 file=sys.stdout):
        self.before_msg = before_msg
        self.after_msg = after_msg
        # self.test = test
        self.file = file
        self.error_msg = error_msg
        # self.timer = timer
        self.start = time.time()

    def __enter__(self):
        if self.before_msg is not None:
            print(self.before_msg, end='', flush=True, file=self.file)
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        if ex_type is None:  # No error
            if self.after_msg is not None:
                # Try formatting
                msg = self.after_msg.format(self.elapsed)
                print(msg, file=self.file)

        # elif self.error_msg is not None:  # Else if there was an error and there is an error message
        #     if self.timer:
        #         print(self.error_msg.format(self.elapsed), file=self.file)
        #     else:
        #         print(self.error_msg, file=self.file)

    @property
    def elapsed(self):
        return time.time() - self.start
