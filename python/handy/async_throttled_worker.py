#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Running large numbers of coroutines a limited number at a time.
"""
import asyncio
import inspect
import logging
import statistics
from asyncio import Event, Queue, Future, Lock
from contextlib import contextmanager
from datetime import timedelta, datetime
from types import FrameType
from typing import Coroutine, Iterable, List, TypeVar, Any, Generic, Awaitable, Optional, Callable, Union

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"

logger = logging.getLogger(__name__)

T = TypeVar("T")
TQ = TypeVar("TQ")


def example():
    async def dowork(val=None):
        # raise Exception("Test exc")
        delay: float = 1 + (id(val) % 10) / 10
        # print(f"Task-{val}, delay={delay}, start")
        await asyncio.sleep(delay)
        print(f"Task-{val}, delay={delay}, end")
        return delay

    async def doworkfast(val=None):
        print(f"[{val}]", datetime.now())
        # if val < 10:
        # await asyncio.sleep(random.random()*1)
        # if val == 12:
        #     await asyncio.sleep(2)

    async def run():
        async with AsyncThrottledWorker(num_workers=3) as atw:
            for i in range(10):
                await atw.submit_nowait(dowork(i))
            await asyncio.sleep(1)
            print(atw.active_work_units)
        #
        # async with AsyncThrottledWorker(num_workers=3, max_hz=2, hz_timebase=timedelta(seconds=5)) as atw:
        #     for i in range(10):
        #         await asyncio.sleep(random.random() * 2)
        #         await atw.submit_nowait(doworkfast(i + 1))

        atw = AsyncThrottledWorker(max_hz=3)

        async def worker(name):
            for i in range(3):
                # x = await atw.submit_wait_to_finish(dowork(f"{name}-{i}"))
                x = await atw.submit_wait_to_start(dowork(f"wait to start {name}-{i}"))
                # x = await atw.submit_nowait(dowork(f"{name}-{i}"))
                print(name, i, x)
                print(atw)

        tasks = []
        for n in ("Larry", "Moe", "Curly"):
            tasks.append(asyncio.create_task(worker(n)))
        await asyncio.gather(*tasks)
        await atw.close()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())


class ThrottledQueue(Queue, Generic[TQ]):
    """
    Releases objects no faster than the given max_hz and hz_timebase.
    Default is one release per second.
    Example, if you want no faster than 3 releases every minute:
        q = ThrottledQueue(max_hz = 3, hz_timebase = timedelta(seconds=60)
    """
    DEFAULT_HZ_TIMEBASE: timedelta = timedelta(seconds=1)
    DEFAULT_MAX_HZ: int = 1

    def __init__(self, max_hz: int = None, hz_timebase: timedelta = None, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.max_hz: int = max_hz or self.DEFAULT_MAX_HZ
        if max_hz <= 0:
            raise Exception(f"Max herz must be a positive integer (was {max_hz})")
        self.hz_timebase: timedelta = hz_timebase or self.DEFAULT_HZ_TIMEBASE
        self._timestamps: List[datetime] = []
        self._lock: Lock = Lock()

    def __str__(self):
        return f"{self.__class__.__name__}(max_hz={self.max_hz}, hz_timebase={self.hz_timebase}, qsize={self.qsize()})"

    async def get(self) -> TQ:
        async with self._lock:
            item = await super().get()
            time_ago = datetime.now() - self.hz_timebase

            # Clean up: Dump all timestamps older than time_ago
            while self._timestamps and self._timestamps[0] < time_ago:
                _ = self._timestamps.pop(0)

            # If we have too many gets within the "time ago", then keep delaying
            while len(self._timestamps) >= self.max_hz:
                delay = self._timestamps[0] - time_ago
                await asyncio.sleep(delay.total_seconds())
                self._timestamps.pop(0)

            self._timestamps.append(datetime.now())
        # print(f"{self} {id(self)} releasing {item}")
        return item

    @staticmethod
    def peek_queue(q: asyncio.Queue) -> List[TQ]:
        """Returns a copy of the queue"""
        items: List[TQ] = list()
        try:
            items.append(q.get_nowait())
        except asyncio.QueueEmpty:
            pass
        for x in items:
            q.put_nowait(x)
            q.task_done()  # We get redundant puts here if we don't mark task done
        return items


class AsyncThrottledWorker:
    # __QUEUE_COMPLETED__ = "__QUEUE_COMPLETED__"
    DEFAULT_NUM_WORKERS: int = 3

    def __init__(self,
                 num_workers: int = None,
                 max_hz: int = None,
                 hz_timebase: timedelta = None):
        """
        Create a throttled queue for which async coroutines can be submitted and executed in a controlled manner.
        :param num_workers: Max number of simultaneous coroutines to be running
        :param max_hz: Max number of coroutines per some time base (default is per second)
        :param hz_timebase: Time base for max_hz (default is one second)
        """
        self.num_workers: int = num_workers or self.DEFAULT_NUM_WORKERS
        self.max_hz: int = max_hz  # Maximum number of times to execute in an amount of time
        self.hz_timebase: timedelta = hz_timebase
        self.todo: asyncio.Queue
        self._active_work_units: List[WorkUnit] = list()

        if max_hz is None:
            self.todo: asyncio.Queue[Optional[WorkUnit]] = asyncio.Queue()
        else:
            self.todo: asyncio.Queue[Optional[WorkUnit]] = ThrottledQueue(max_hz=max_hz, hz_timebase=hz_timebase)
        for _ in range(self.num_workers):
            asyncio.create_task(self._worker())

    @property
    def active_work_units(self) -> List["WorkUnit"]:
        return list(self._active_work_units)

    def __str__(self):
        items = ThrottledQueue.peek_queue(self.todo)
        avg_age = timedelta(seconds=statistics.mean(x.age.total_seconds() for x in items)) \
            if items else timedelta()
        return f"{self.__class__.__name__}(" \
               f"qSize={self.todo.qsize():,}, " \
               f"avgAge={human_duration(avg_age)}, " \
               f"numWorkers={self.num_workers:,}, " \
               f"maxHz={self.max_hz}, " \
               f"hzTimebase={self.hz_timebase})"

    def __repr__(self):
        return self.__str__()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # print(f"{self.__class__.__name__}.__aexit__ ({exc_type}, {exc}, {tb})")
        for _ in range(self.num_workers):
            await self.todo.put(None)
        await self.todo.join()
        if exc:
            raise exc

    async def close(self):
        await self.__aexit__(None, None, None)

    def throttle(self, obj_func: Awaitable):
        """Throttles an object's awaitable function/coroutine."""
        orig_func = getattr(obj_func.__self__, obj_func.__name__)

        async def wrapped_func(*args, **kwargs):
            return await self.submit_wait_to_finish(orig_func(*args, **kwargs),
                                                    name=f"from:{inspect.currentframe().f_back.f_back.f_code.co_name}."
                                                         f"{inspect.currentframe().f_back.f_code.co_name}")

        setattr(obj_func.__self__, obj_func.__name__, wrapped_func)

    async def submit_nowait(self, coro: Coroutine[Any, Any, T], name: Union[str, Callable] = None) -> Future[T]:
        """Submits a coroutine to be executed and returns immediately with a Future object
        representing the eventual result of the coroutine."""
        fut = asyncio.get_event_loop().create_future()
        await self.todo.put(WorkUnit(coro, fut, name))
        return fut

    async def submit_batch(self, coros: Iterable[Coroutine], name: Union[str, Callable] = None) -> List[Future]:
        """Submits a group of coroutines to be executed and returns immediately with a list
        of Future objects representing the eventual results of the coroutines."""
        futs = []
        for c in coros:
            futs.append(await self.submit_nowait(c, name=name))
        return futs

    async def submit_wait_to_start(self, coro: Coroutine[Any, Any, T], name: Union[str, Callable] = None) -> Future[T]:
        """Submits a coroutine to be executed and returns once the coroutine has
        been scheduled (execution is imminent).
        Returns a Future object representing the eventual result of the coroutine."""
        fut = asyncio.get_event_loop().create_future()
        start_event = Event()

        async def _wait_to_start_wrapper(_c) -> Future:
            start_event.set()
            return await _c

        await self.submit_nowait(_wait_to_start_wrapper(coro), name=name)
        await start_event.wait()
        return fut

    async def submit_wait_to_finish(self, coro: Coroutine[Any, Any, T], name: Union[str, Callable] = None) -> T:
        """Submits a coroutine to be executed and returns once the coroutine has completed.
        Returns a Future object representing the result of the coroutine.
        Effectively stalls out the program until all previous work is completed."""
        fut = await self.submit_nowait(coro, name=name)
        await fut  # Waits for coroutine to be completed
        return fut.result()

    async def drain(self):
        """Waits until all submitted coroutines have been executed by calling join() on the Queue"""
        await self.todo.join()

    async def _worker(self):
        """Executes coroutines"""
        completed: bool = False
        while not completed:
            try:
                work = await self.todo.get()
            except Exception as ex:
                logger.error(f"Error while retrieving next work unit: {ex}")
                # traceback.print_tb(sys.exc_info()[2])
            else:
                if work is None:
                    completed = True
                else:
                    with self.active_work_unit(work):
                        await work.run()
                self.todo.task_done()
        # print("THE WORKER FINISHED! REALLY?")

    @contextmanager
    def active_work_unit(self, _w: "WorkUnit") -> "WorkUnit":
        """Used with the wait_for_tasking_to_complete"""
        self._active_work_units.append(_w)
        try:
            yield _w
        finally:
            self._active_work_units.remove(_w)


class WorkUnit:
    def __init__(self, coro: Coroutine, fut: asyncio.Future, name: Union[str, Callable] = None):
        self.coro: Coroutine = coro
        self.fut: asyncio.Future = fut
        self.name: Union[str, Callable] = name
        self.start: Optional[datetime] = None
        self.stop: Optional[datetime] = None
        self.created_at: datetime = datetime.now()
        self.source_frame: FrameType = inspect.currentframe().f_back
        # if self.source_frame:
        #     self.source_frame.clear()

    def __str__(self):
        n = self.name() if callable(self.name) else self.name
        fields = [f"name={n}"]
        if self.start:
            fields.append(f"runningTime={human_duration(self.running_time())}")
        fields.append(f"timeInQueue={human_duration(self.age)}")
        fields.append(f"coro={self.coro}")
        # if self.source_frame:
        #     fields.append(f"frame={self.source_frame.f_code.co_name}")
        # x = self.source_frame

        return f"{self.__class__.__name__}({', '.join(fields)})"

    def __repr__(self):
        return self.__str__()

    @property
    def age(self) -> timedelta:
        return datetime.now() - self.created_at

    def running_time(self) -> Optional[timedelta]:
        return datetime.now() - self.start if self.start else None

    async def run(self):
        self.start = datetime.now()
        try:
            result = await self.coro
        except Exception as ex:
            self.stop = datetime.now()
            logger.debug(f"WorkUnit caught an exception - it will be passed with the Future: {type(ex)}: {ex}")
            self.fut.set_exception(ex)
        else:
            self.stop = datetime.now()
            self.fut.set_result(result)
        return self.fut


if __name__ == '__main__':
    try:
        example()
    except KeyboardInterrupt:
        pass
