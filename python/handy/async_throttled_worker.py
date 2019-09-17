#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Managing coroutines
"""
import asyncio
from asyncio import Event, Queue, Future
import sys
from typing import Coroutine, Optional, Iterable, List

from tqdm import tqdm


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())


async def run():
    # print(await batch1(10))
    # print(await batch2(10, 3))
    # print(await batch3(10, 3))
    print(await batch6(10, 2))


# async def batch1(num_tasks):
#     tasks = [dowork(i) for i in range(num_tasks)]
#     results = await asyncio.gather(*tasks)
#     return results
#
#
# async def batch2(num_tasks, num_workers):
#     q_in = Queue()
#     q_out = Queue()
#
#     for i in range(num_tasks):
#         q_in.put_nowait(dowork(i))
#
#     async def _worker():
#         while q_in.qsize():
#             task = await q_in.get()
#             result = await task
#             await q_out.put(result)
#
#     workers = [_worker() for _ in range(num_workers)]
#     await asyncio.gather(*workers)
#     data = []
#     while q_out.qsize():
#         data.append(q_out.get_nowait())
#     return data
#
#
# async def batch3(num_tasks, num_workers):
#     things_to_process = list(range(num_tasks))
#     data = []
#     async with AsyncThrottledWorker(num_workers) as atw:
#         for x in tqdm(things_to_process):
#             await atw.submit(dowork(x))
#         print("Sleeping...", end="", flush=True)
#         await asyncio.sleep(3)
#         print("Awake")
#     return data


# class AsyncThrottledWorker:
#     def __init__(self, num_workers: int = 3):
#         self.num_workers: int = num_workers
#         self.queue_in = Queue(maxsize=num_workers)
#         self.queue_out = Queue()
#         self.workers = list()
#         self.is_running = False
#
#     async def __aenter__(self):
#         self.is_running = True
#
#         async def _worker():
#             while self.is_running:
#                 coro = await self.queue_in.get()
#                 result = await coro
#                 await self.queue_out.put(result)
#
#         for _ in range(self.num_workers):
#             w = _worker()
#             self.workers.append(w)
#             asyncio.get_event_loop().create_task(w)
#
#         return self
#
#     async def __aexit__(self):
#         self.is_running = False
#         await self.queue_in.join()  # Wait until jobs are all retrieved
#         # TODO left off here
#         pass
#
#     async def submit(self, coro: Coroutine):
#         await self.queue_in.put(coro)

#
# async def batch4(num_tasks, num_workers):
#     things_to_process = list(range(num_tasks))
#     async with AsyncThrottledWorker4(num_workers) as atw:
#         # for x in (things_to_process):
#         #     await atw.submit(dowork(x))
#         await atw.submit_batch([dowork(x) for x in things_to_process])
#     return atw.results
#
#
# class AsyncThrottledWorker4:
#     def __init__(self, num_workers: int = 3):
#         self.num_workers: int = num_workers
#         self.workers_available: asyncio.Queue = asyncio.Queue()
#         self.workers_in_use: asyncio.Queue = asyncio.Queue()
#         self.results: asyncio.Queue = asyncio.Queue()
#
#     async def __aenter__(self):
#         for _ in range(self.num_workers):
#             await self.workers_available.put(1)
#         return self
#
#     async def __aexit__(self, exc_type, exc, tb):
#         await self.workers_in_use.join()
#
#     async def submit(self, coro: Coroutine):
#         async def _wrap(_coro: Coroutine):
#             try:
#                 _result = await _coro  # Do the work
#             except Exception as ex:
#                 await self.results.put((type(ex), ex, sys.exc_info()[2], _coro))
#             else:
#                 await self.results.put(_result)
#
#             await self.workers_available.put(1)  # Make worker available again
#             await self.workers_in_use.get()  # Opposite, marke worker free
#             self.workers_in_use.task_done()  # Mark worker free this way also
#
#         await self.workers_available.get()
#         await self.workers_in_use.put(asyncio.create_task(_wrap(coro)))
#
#     async def submit_batch(self, coros: Iterable[Coroutine]):
#         """Submits all coroutines at once and returns immediately"""
#
#         async def _submit_in_turn(_coros: Iterable[Coroutine]):
#             for c in _coros:
#                 await self.submit(c)
#
#         asyncio.create_task(_submit_in_turn(coros))


async def batch5(num_tasks, num_workers):
    things_to_process = [dowork(x) for x in range(num_tasks)]
    async with AsyncThrottledWorker5(num_workers) as atw:
        # await atw.submit_batch(things_to_process)
        for x in (things_to_process):
            #     await atw.submit_and_wait_to_finish(x)
            await atw.submit_and_wait_to_start(x)
    return atw.results


class AsyncThrottledWorker5:
    """
    This version works, but I think it can be better if I expose a more direct path
    to the underlying tasks and their Future objects etc.
    """
    __QUEUE_COMPLETED__ = "__QUEUE_COMPLETED__"

    def __init__(self, num_workers: int = 3):
        self.num_workers = 3
        self.todo: asyncio.Queue
        self.results: Iterable
        # This queue holds tuples with the following elements:
        #  0: The Coroutine to run
        #  1: An asyncio.Event to mark that coroutine has started
        #  2: An asyncio.Event to mark that the coroutine has ended
        #  3: An asyncio.Queue to hold the result of the coroutine

    async def __aenter__(self):
        self.todo = Queue()
        self.results = []
        for i in range(self.num_workers):
            asyncio.create_task(self._executor(f"Exec-{i + 1}"))
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # print("__aexit__")
        for _ in range(self.num_workers):
            await self.todo.put(self.__QUEUE_COMPLETED__)
        await self.todo.join()

    async def submit_nowait(self, coro: Coroutine):
        start_event, end_event, result_queue = Event(), Event(), Queue()
        await self.todo.put((coro, start_event, end_event, result_queue))
        return result_queue

    async def submit_and_wait_to_start(self, coro: Coroutine):
        start_event, end_event, result_queue = Event(), Event(), Queue()
        await self.todo.put((coro, start_event, end_event, result_queue))
        await start_event.wait()

    async def submit_and_wait_to_finish(self, coro: Coroutine):
        start_event, end_event, result_queue = Event(), Event(), Queue()
        await self.todo.put((coro, start_event, end_event, result_queue))
        await end_event.wait()
        result = await result_queue.get()
        return result

    async def submit_batch(self, coros: Iterable[Coroutine]):
        for c in coros:
            await self.submit_nowait(c)

    async def _executor(self, name):
        # print(f"_executor {name} starting")
        completed: bool = False
        while not completed:
            work = await self.todo.get()
            if work == self.__QUEUE_COMPLETED__:
                completed = True
            else:
                coro, start_event, end_event, result_queue = work  # type: Coroutine, Event, Event, Queue
                start_event.set()

                try:
                    result = await coro
                except Exception as ex:
                    result = (type(ex), ex, sys.exc_info()[2], coro)

                self.results.append(result)
                await result_queue.put(result)
                end_event.set()

            self.todo.task_done()

        # print(f"_executor {name} exiting")


async def batch6(num_tasks, num_workers):
    things_to_process = [dowork(x) for x in range(num_tasks)]
    async with AsyncThrottledWorker6(num_workers) as atw:
        results = []
        # for c in (things_to_process):
        for i in range(len(things_to_process)):
            c = things_to_process[i]
            print("Preparing", c)
            if i < 5:
                r = await atw.submit_nowait(c)
            elif i == 5:
                print("THIS ONE WILL STALL EVERYTHING", c)
                r = await atw.submit_wait_to_finish(c)
            else:
                r = await atw.submit_nowait(c)
            # r = await atw.submit_wait_to_start(c)
            # r = await atw.submit_wait_to_finish(c)
            results.append(r)

            # if i % 3 == 0:
            #     print("DRAINING")
            #     await atw.drain()
            #     print("DRAIN COMPLETE")

    # result_vals = asyncio.gather(*results)
    # for v in result_vals:
    #     print(v)
    for r in results:
        try:
            print(await r)
        except Exception as ex:
            print("EX RAISED:", ex)
    print("batch6 exiting")


async def dowork(val=None):
    offset = 1
    delay: float = offset + (id(val) % 10) / 10
    # delay = val
    print(f"Task-{val}, delay={delay}, start")
    if delay <= offset + 0.1:
        raise Exception(f"Problem with delay {delay}")
    await asyncio.sleep(delay)
    print(f"Task-{val}, delay={delay}, end")
    return delay


class AsyncThrottledWorker6:
    __QUEUE_COMPLETED__ = "__QUEUE_COMPLETED__"

    def __init__(self, num_workers: int = 3):
        self.num_workers = num_workers
        self.todo: Queue

    async def __aenter__(self):
        self.todo = Queue()
        for i in range(self.num_workers):
            asyncio.create_task(self._worker(f"Worker-{i + 1}"))
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

    async def _wrap(self, coro: Coroutine, fut: Future) -> Future:
        """Used internally to tie a coroutine to a future with proper result/exception handling."""
        try:
            result = await coro
        except Exception as ex:
            fut.set_exception(ex)
        else:
            fut.set_result(result)
        return fut

    async def _worker(self, name: str = None):
        """Executes coroutines"""
        completed: bool = False
        while not completed:
            work = await self.todo.get()
            if work == self.__QUEUE_COMPLETED__:
                completed = True
            else:
                await work
            self.todo.task_done()


AsyncThrottledWorker = AsyncThrottledWorker6

if __name__ == '__main__':
    main()
