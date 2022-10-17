#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper asyncio queue.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from typing import List, TypeVar

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AdvancedAsyncQueue(asyncio.Queue[T]):
    """Like a regular asyncio.Queue but if there's an exception while getting an object out,
    the object goes back in the queue."""

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.hold: asyncio.Lock = asyncio.Lock()

    @asynccontextmanager
    async def get_all_if_any_and_block(self) -> List[T]:
        """Returns all items in queue, or an empty list, and blocks until
        the with block is processed.  This allows a convenient pattern
        where you can work on a batch of items with tasks that will expire.
        """
        async with self.hold:
            all_items = await self.get_all_if_any()
            yield all_items

    def peek(self) -> List[T]:
        return list(self._queue)

    async def get_all_if_any(self) -> List[T]:
        """Gets all items but returns immediately of queue is empty"""
        all = []
        try:
            while True:
                all.append(self.get_nowait())
        except asyncio.queues.QueueEmpty:
            pass
        return all

    async def get_all(self) -> List[T]:
        """Gets all items from the queue."""
        all = [await self.get()]
        try:
            while True:
                all.append(self.get_nowait())
        except asyncio.queues.QueueEmpty:
            pass
        return all

    async def put_all(self, values: List[T]):
        """Puts all the items from the list individually in the queue, signalling when the last item is added"""
        if len(values) == 0:
            pass
        elif len(values) == 1:
            await self.put(values[0])
        else:
            for v in values[:-1]:  # Put all but the last item without any async signaling
                self.put_nowait(v)
            await self.put(values[-1])  # Put the last item in with async signal

    @asynccontextmanager
    async def get_unless_exception(self) -> T:
        """

        async with queue.get_unless_exception() as x:
            blah(x)
            blahblah(x)
            # Exception is raised!

        # queue will have x in it again



        :return:
        """
        obj = await self.get()
        try:
            yield obj
        except Exception as ex:
            # Put obj back in queue
            objs = [obj]
            try:
                while True:
                    objs.append(self.get_nowait())
            except asyncio.queues.QueueEmpty:
                pass
            for o in objs:
                self.put_nowait(o)
                self.task_done()  # Need to account for double-counting of putting in and taking out
            self.task_done()  # Plus one for the obj we just took out
            raise ex
        else:
            pass
