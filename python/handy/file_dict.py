#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A file-backed dictionary.
"""

import gzip as gziplib
import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from time import sleep

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"
__homepage__ = "https://github.com/rharder/handy"

from pprint import pprint

from typing import Optional

logger = logging.getLogger(__name__)


def example():
    logging.basicConfig(level=logging.DEBUG)
    filename = "example.json"
    # filename = None
    x = {"a": "b"}
    fd = FileDict(filename, {"a": "b"})
    fd.reload_before_read = True
    fd.update({1: 1, 2: 2})
    # fd = FileDict()
    # fd.filename = filename
    # fd.reload(filename)
    print("fd", fd)
    fd["hello"] = "world"
    print("fd", fd)
    print("fd['a'] = ", fd['a'])
    # fd["b"] = "c"
    # with fd:
    #     fd["c"] = "c"
    #     fd["d"] = "d"
    # filename = "example.json"
    # fd.force_save(filename)
    with exclusive_open(filename) as f:
        print(f"{filename} CONTENTS: ", f.read())
    pprint(fd)


class FileDict(dict):

    def __init__(self, filename: str = None, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.filename = filename
        self.gzip: bool = self.filename.lower().endswith(".gz") if self.filename else False
        self._indent: Optional[int] = None
        self._suspend_save: bool = True
        self._reload_before_read: bool = False

        _elements_received_in_constructor: bool = len(self) > 0

        # Load from existing file
        if self.filename:
            try:
                if self.gzip:
                    with gziplib.open(self.filename, "rt") as f:
                        d = json.load(f)
                    logger.debug(f"Loaded {len(d):,} initial entries from {self.filename}")
                else:
                    with exclusive_open(self.filename) as f:
                        d = json.load(f)
                    logger.debug(f"Loaded {len(d):,} initial entries from {self.filename}")
            except FileNotFoundError as ex:
                # print(type(ex), ex)
                pass
            except json.JSONDecodeError as ex:
                logger.error(f"Error reading json file {self.filename}: {ex}")
            else:
                super().update(d)

        if _elements_received_in_constructor:
            # print("Saving because we had elements in the constructor")
            self.force_save()
        self._suspend_save = False

    @property
    def indent(self):
        return self._indent

    @indent.setter
    def indent(self, val):
        self._indent = val
        self.force_save()

    @property
    def reload_before_read(self):
        return self._reload_before_read

    @reload_before_read.setter
    def reload_before_read(self, val):
        self._reload_before_read = bool(val)

    def set_indent(self, val):
        """
        Sets the indent and returns self so you can chain a constructor.
        :param val: indent value or None if no indent
        :return: FileDict self
        :rtype: FileDict
        """
        self.indent = val
        return self

    def set_reload_before_read(self, val):
        """
        Sets reload_before_read and returns self so you can chain a constructor.
        :param val: reload_before_read true or false
        :return: FileDict self
        :rtype: FileDict
        """
        self.reload_before_read = val
        return self

    def __getitem__(self, k):
        if self.reload_before_read and not self._suspend_save:
            self.reload()
        return super().__getitem__(k)

    def __enter__(self):
        self._suspend_save = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._suspend_save = False
        self.force_save()
        if exc_val:
            raise exc_val

    def __setitem__(self, key, val):
        dict.__setitem__(self, key, val)
        if not self._suspend_save:
            self.force_save()

    def update(self, *args, **kwargs):
        with self:  # Suspend save until all updates are complete
            super().update(*args, **kwargs)

    def force_save(self, filename: str = None, gzip: bool = None):
        if filename:
            if gzip is None:
                gzip = filename.lower().endswith(".gz")  # Infer from filename
        else:
            filename = self.filename
            gzip = self.gzip

        if filename:
            d = dict(self)
            if gzip:
                with gziplib.open(filename, "wt") as f:
                    json.dump(d, f, indent=self.indent, default=str)
                logger.debug(f"Saved {len(d):,} entries to {self.filename}")
            else:
                with exclusive_open(filename, "w") as f:
                    json.dump(d, f, indent=self.indent, default=str)
                logger.debug(f"Saved {len(d):,} entries to {self.filename}")

    def reload(self, filename: str = None):
        filename = filename or self.filename
        if filename:
            gzip: bool = filename.lower().endswith(".gz")
            if gzip:
                with gziplib.open(filename, "rt") as f:
                    d = json.load(f)
                logger.debug(f"Reloaded {len(d):,} entries from {filename}")
            else:
                with exclusive_open(filename) as f:
                    d = json.load(f)
                logger.debug(f"Reloaded {len(d):,} entries from {filename}")
            super().clear()
            super().update(d)


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
    lockfile = filename + ".lock"
    if timeout is not None:
        deadline = datetime.now() + timedelta(seconds=timeout)
    while True:
        try:
            fd = os.open(lockfile, os.O_CREAT | os.O_EXCL)
            break
        except FileExistsError:
            if timeout is not None and datetime.now() >= deadline:
                raise
            sleep(retry_time)
    try:
        with open(filename, *args, **kwargs) as f:
            yield f
    finally:
        try:
            os.close(fd)
        finally:
            os.unlink(lockfile)


if __name__ == '__main__':
    example()
