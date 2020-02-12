#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A file-backed dictionary.
"""

import gzip as gziplib
import json
import logging

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"
__homepage__ = "https://github.com/rharder/handy"

logger = logging.getLogger(__name__)

def example():
    filename = "example.json"
    # filename = None
    x = {"a": "b"}
    fd = FileDict(filename, {"a": "b"})
    fd.update({1: 1, 2: 2})
    # fd = FileDict()
    # fd.filename = filename
    # fd.reload(filename)
    print("fd", fd)
    fd["hello"] = "world"
    print("fd", fd)
    # fd["b"] = "c"
    # with fd:
    #     fd["c"] = "c"
    #     fd["d"] = "d"
    # filename = "example.json"
    # fd.force_save(filename)
    with open(filename) as f:
        print(f"{filename} CONTENTS: ", f.read())


class FileDict(dict):
    def __init__(self, filename: str = None, *kargs, **kwargs):
        self.filename = filename
        self.gzip: bool = self.filename.lower().endswith(".gz") if self.filename else False
        self.indent = None
        self._suspend_save = True

        super().__init__(*kargs, **kwargs)
        _elements_received_in_constructor: bool = len(self) > 0

        # Load from existing file
        if self.filename:
            try:
                if self.gzip:
                    with gziplib.open(self.filename, "rt") as f:
                        d = json.load(f)
                    logger.info(f"Loaded {len(d):,} entries from {self.filename}")
                else:
                    with open(self.filename) as f:
                        d = json.load(f)
                    logger.info(f"Loaded {len(d):,} entries from {self.filename}")
            except FileNotFoundError as ex:
                # print(type(ex), ex)
                pass
            else:
                super().update(d)

        if _elements_received_in_constructor:
            # print("Saving because we had elements in the constructor")
            self.force_save()
        self._suspend_save = False

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
                    json.dump(d, f, indent=self.indent)
                logger.info(f"Saved {len(d):,} entries to {self.filename}")
            else:
                with open(filename, "w") as f:
                    json.dump(d, f, indent=self.indent)
                logger.info(f"Saved {len(d):,} entries to {self.filename}")

    def reload(self, filename: str = None):
        filename = filename or self.filename
        if filename:
            gzip: bool = filename.lower().endswith(".gz")
            if gzip:
                with gziplib.open(filename, "rt") as f:
                    d = json.load(f)
                logger.info(f"Reloaded {len(d):,} entries from {filename}")
            else:
                with open(filename) as f:
                    d = json.load(f)
                logger.info(f"Reloaded {len(d):,} entries from {filename}")
            super().update(d)


if __name__ == '__main__':
    example()
