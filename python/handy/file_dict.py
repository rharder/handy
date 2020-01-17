#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A file-backed dictionary.
"""
import asyncio
import gzip as gziplib
import json
from concurrent.futures.thread import ThreadPoolExecutor

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"
__homepage__ = "https://github.com/rharder/handy"


def example():
    asyncio.get_event_loop().set_debug(True)
    filename = "example.json"
    # filename = None
    x = {"a": "b"}
    fd = FileDict(filename, {"a": "b"})
    # fd.update({1: 1, 2: 2})
    # with fd:
    #     for x in range(1000):
    #         k = "hello world " * x
    #         v = "hello world " * x
    #         fd[k] = v
    # fd = FileDict()
    # fd.filename = filename
    # fd.reload(filename)
    # print("fd", fd)
    # fd["hello"] = "world"
    # print("fd", fd)
    # fd["b"] = "c"
    # with fd:
    #     fd["c"] = "c"
    #     fd["d"] = "d"
    # filename = "example.json"
    # fd.force_save(filename)
    # with open(filename) as f:
    #     print(f"{filename} CONTENTS: ", f.read())

    async def run():
        print("reading async")
        fd2 = await FileDict.async_load("example.json")
        print(f"Read items: {len(fd2.keys()):,}")
        async with fd2:
            fd2["added async"] = "here"
            fd2["also async"] = "here also"

            print("Adding records")
            for x in range(1000):
                k = "hello world " * x
                v = "hello world " * x
                fd2[k] = v
        print("done")

        # print(fd)

    asyncio.get_event_loop().run_until_complete(run())


class FileDict(dict):
    EXEC: ThreadPoolExecutor = None

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
                else:
                    with open(self.filename) as f:
                        d = json.load(f)
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

    @staticmethod
    async def async_load(filename):
        FileDict.EXEC = FileDict.EXEC or ThreadPoolExecutor()
        fd = await asyncio.get_event_loop().run_in_executor(FileDict.EXEC, FileDict, filename)
        return fd

    async def __aenter__(self):
        self._suspend_save = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._suspend_save = False
        FileDict.EXEC = FileDict.EXEC or ThreadPoolExecutor()
        await asyncio.get_event_loop().run_in_executor(FileDict.EXEC, self.force_save)
        if exc_val:
            raise exc_val

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
            # print(f"Saving to {filename}:", self)
            if gzip:
                with gziplib.open(filename, "wt") as f:
                    json.dump(self, f, indent=self.indent)
            else:
                with open(filename, "w") as f:
                    json.dump(self, f, indent=self.indent)

    def reload(self, filename: str = None):
        filename = filename or self.filename
        if filename:
            gzip: bool = filename.lower().endswith(".gz")
            if gzip:
                with gziplib.open(filename, "rt") as f:
                    d = json.load(f)
            else:
                with open(filename) as f:
                    d = json.load(f)
            super().update(d)


if __name__ == '__main__':
    example()
