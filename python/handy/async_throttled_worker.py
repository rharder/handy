#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Running large numbers of coroutines a limited number at a time.
"""
import asyncio
from asyncio import Event, Queue, Future
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

    async def run():
        async with AsyncThrottledWorker(num_workers=3) as atw:
            for i in range(10):
                await atw.submit_nowait(dowork(i))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())


class AsyncThrottledWorker:
    __QUEUE_COMPLETED__ = "__QUEUE_COMPLETED__"

    def __init__(self, num_workers: int = 3):
        self.num_workers = num_workers
        self.todo: Queue

    async def __aenter__(self):
        self.todo = Queue()
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
