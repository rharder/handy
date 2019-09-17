#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Managing coroutines
"""
import asyncio
from asyncio import Event, Queue
import sys
from typing import Coroutine, Optional, Iterable

from tqdm import tqdm


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())


async def run():
    # print(await batch1(10))
    # print(await batch2(10, 3))
    # print(await batch3(10, 3))
    print(await batch5(10, 3))


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


async def batch4(num_tasks, num_workers):
    things_to_process = list(range(num_tasks))
    async with AsyncThrottledWorker4(num_workers) as atw:
        # for x in (things_to_process):
        #     await atw.submit(dowork(x))
        await atw.submit_batch([dowork(x) for x in things_to_process])
    return atw.results


class AsyncThrottledWorker4:
    def __init__(self, num_workers: int = 3):
        self.num_workers: int = num_workers
        self.workers_available: asyncio.Queue = asyncio.Queue()
        self.workers_in_use: asyncio.Queue = asyncio.Queue()
        self.results: asyncio.Queue = asyncio.Queue()

    async def __aenter__(self):
        for _ in range(self.num_workers):
            await self.workers_available.put(1)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.workers_in_use.join()

    async def submit(self, coro: Coroutine):
        async def _wrap(_coro: Coroutine):
            try:
                _result = await _coro  # Do the work
            except Exception as ex:
                await self.results.put((type(ex), ex, sys.exc_info()[2], _coro))
            else:
                await self.results.put(_result)

            await self.workers_available.put(1)  # Make worker available again
            await self.workers_in_use.get()  # Opposite, marke worker free
            self.workers_in_use.task_done()  # Mark worker free this way also

        await self.workers_available.get()
        await self.workers_in_use.put(asyncio.create_task(_wrap(coro)))

    async def submit_batch(self, coros: Iterable[Coroutine]):
        """Submits all coroutines at once and returns immediately"""

        async def _submit_in_turn(_coros: Iterable[Coroutine]):
            for c in _coros:
                await self.submit(c)

        asyncio.create_task(_submit_in_turn(coros))


async def batch5(num_tasks, num_workers):
    things_to_process = list(range(num_tasks))
    async with AsyncThrottledWorker4(num_workers) as atw:
        # for x in (things_to_process):
        #     await atw.submit(dowork(x))
        await atw.submit_batch([dowork(x) for x in things_to_process])
    return atw.results


class AsyncThrottledWorker5:
    def __init__(self, num_workers: int = 3):
        self.num_workers = 3
        self.todo: asyncio.Queue
        # This queue holds tuples with the following elements:
        #  0: The Coroutine to run
        #  1: An asyncio.Event to mark that coroutine has started
        #  2: An asyncio.Event to mark that the coroutine has ended
        #  3: An asyncio.Queue to hold the result of the coroutine

    async def __aenter__(self):
        self.todo = asyncio.Queue()
        asyncio.create_task(self._executor())
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.todo.join()

    async def submit_nowait(self, coro: Coroutine):
        start_event, end_event, result_queue = Event(), Event(), Queue()
        await self.todo.put((coro, start_event, end_event, result_queue))

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

    async def _executor(self):
        work = await self.todo.get()



async def dowork(val=None):
    delay: float = 1 + (id(val) % 10) / 10
    # delay = val
    print(f"Delay({delay})")
    if delay <= 1.1:
        raise Exception(f"Problem with delay {delay}")
    await asyncio.sleep(delay)
    return delay


if __name__ == '__main__':
    main()
