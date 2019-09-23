#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Running large numbers of coroutines a limited number at a time.
"""
import asyncio
import datetime
import math
import random
import sys
from asyncio import Event, Queue, Future, Lock
from typing import Coroutine, Iterable, List

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


def example():
    async def dowork(val=None):
        delay: float = 1 + (id(val) % 10) / 10
        print(f"Task-{val}, delay={delay}, start")
        await asyncio.sleep(delay)
        print(f"Task-{val}, delay={delay}, end")
        return delay

    async def doworkfast(val=None):
        print(f"[{val}]", datetime.datetime.now())
        # if val < 10:
        # await asyncio.sleep(random.random()*1)
        # if val == 12:
        #     await asyncio.sleep(2)

    async def run():
        # async with AsyncThrottledWorker(num_workers=3) as atw:
        #     for i in range(10):
        #         await atw.submit_nowait(dowork(i))

        async with AsyncThrottledWorker(num_workers=3, max_hz=2, hz_timebase=datetime.timedelta(seconds=5)) as atw:
            for i in range(10):
                await asyncio.sleep(random.random() * 2)
                await atw.submit_nowait(doworkfast(i + 1))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())


class ThrottledQueue(Queue):
    """
    Releases objects no faster than the given max_hz and hz_timebase.
    Default is one release per second.
    Example, if you want no faster than 3 releases every minute:
        q = ThrottledQueue(max_hz = 3, hz_timebase = datetime.timedelta(seconds=60)
    """

    def __init__(self, max_hz: int = None, hz_timebase: datetime.timedelta = None, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.max_hz: int = max_hz or 1
        if max_hz <= 0:
            raise Exception(f"Max herz must be a positive integer (was {max_hz})")
        self.hz_timebase: datetime.timedelta = hz_timebase or datetime.timedelta(seconds=1)
        self._timestamps: List[datetime.datetime] = []
        self._lock: Lock = Lock()

    async def get(self):
        async with self._lock:
            item = await super().get()
            time_ago = datetime.datetime.now() - self.hz_timebase

            # Clean up: Dump all timestamps older than time_ago
            while self._timestamps and self._timestamps[0] < time_ago:
                _ = self._timestamps.pop(0)

            # If we have too many gets within the "time ago", then keep delaying
            while len(self._timestamps) >= self.max_hz:
                delay = self._timestamps[0] - time_ago
                await asyncio.sleep(delay.total_seconds())
                self._timestamps.pop(0)

            self._timestamps.append(datetime.datetime.now())
        return item


class AsyncThrottledWorker:
    __QUEUE_COMPLETED__ = "__QUEUE_COMPLETED__"

    def __init__(self,
                 num_workers: int = 3,
                 max_hz: int = None,
                 hz_timebase: datetime.timedelta = None):
        self.num_workers: int = num_workers
        self.max_hz: int = max_hz  # Maximum number of times to execute in an amount of time
        self.hz_timebase: datetime.timedelta = hz_timebase
        self.todo: Queue

    async def __aenter__(self):
        if self.max_hz is None:
            self.todo = Queue()
        else:
            self.todo = ThrottledQueue(max_hz=self.max_hz, hz_timebase=self.hz_timebase)
        # self._timestamps_this_second = list()
        for _ in range(self.num_workers):
            asyncio.create_task(self._worker())
        return self

    async def __aexit__(self, exc_type, exc, tb):
        assert exc_type is None
        assert exc is None
        assert tb is None

        for _ in range(self.num_workers):
            await self.todo.put(self.__QUEUE_COMPLETED__)
        await self.todo.join()

    async def submit_nowait(self, coro: Coroutine) -> Future:
        """Submits a coroutine to be executed and returns immediately with a Future object
        representing the eventual result of the coroutine."""
        fut = asyncio.get_event_loop().create_future()
        await self.todo.put(self._wrap(coro, fut))
        return fut

    async def submit_batch(self, coros: Iterable[Coroutine]) -> List[Future]:
        """Submits a group of coroutines to be executed and returns immediately with a list
        of Future objects representing the eventual results of the coroutines."""
        futs = []
        for c in coros:
            futs.append(await self.submit_nowait(c))
        return futs

    async def submit_wait_to_start(self, coro: Coroutine) -> Future:
        """Submits a coroutine to be executed and returns once the coroutine has
        been scheduled (execution is imminent).
        Returns a Future object representing the eventual result of the coroutine."""
        fut = asyncio.get_event_loop().create_future()
        start_event = Event()

        async def _wait_to_start_wrapper(_c, _f) -> Future:
            start_event.set()
            return await self._wrap(_c, _f)

        await self.todo.put(_wait_to_start_wrapper(coro, fut))
        await start_event.wait()
        return fut

    async def submit_wait_to_finish(self, coro: Coroutine) -> Future:
        """Submits a coroutine to be executed and returns once the coroutine has completed.
        Returns a Future object representing the result of the coroutine.
        Effectively stalls out the program until all previous work is completed."""
        fut = await self.submit_nowait(coro)
        await fut  # Waits for coroutine to be completed
        return fut

    async def drain(self):
        """Waits until all submitted coroutines have been executed."""
        await self.todo.join()

    @staticmethod
    async def _wrap(coro: Coroutine, fut: Future) -> Future:
        """Used internally to tie a coroutine to a future with proper result/exception handling."""
        try:
            result = await coro
        except Exception as ex:
            fut.set_exception(ex)
        else:
            fut.set_result(result)
        return fut

    async def _worker(self):
        """Executes coroutines"""
        completed: bool = False
        while not completed:
            work = await self.todo.get()
            if work == self.__QUEUE_COMPLETED__:
                completed = True
            else:
                await work
            self.todo.task_done()


if __name__ == '__main__':
    example()
