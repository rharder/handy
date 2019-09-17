#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Managing coroutines
"""
import asyncio
import sys
from asyncio import Queue
from typing import Coroutine, Optional

from tqdm import tqdm


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())


async def run():
    # print(await batch1(10))
    # print(await batch2(10, 3))
    # print(await batch3(10, 3))
    print(await batch4(10, 3))


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
        for x in (things_to_process):
            await atw.submit(dowork(x))
    return atw.results


class AsyncThrottledWorker4:
    def __init__(self, num_workers: int = 3):
        self.num_workers: int = num_workers
        self.workers_available = Queue()
        self.workers_in_use = Queue()
        self.results = []

    async def __aenter__(self):
        for _ in range(self.num_workers):
            await self.workers_available.put(1)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.workers_in_use.join()

    async def submit(self, coro: Coroutine):
        async def _wrap(_coro: Coroutine):
            try:
                result = await _coro  # Do the work
            except Exception as ex:
                self.results.append((type(ex), ex, sys.exc_info()[2]))
            else:
                self.results.append(result)

            await self.workers_available.put(1)  # Make worker available again
            await self.workers_in_use.get()  # Opposite, marke worker free
            self.workers_in_use.task_done()  # Mark worker free this way also

        await self.workers_available.get()
        await self.workers_in_use.put(asyncio.create_task(_wrap(coro)))


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
