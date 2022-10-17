#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
from unittest import TestCase

from handy.advanced_queue import AdvancedAsyncQueue


class TestAdvancedQueue(TestCase):

    def test_get_all(self):
        async def _t():
            q = AdvancedAsyncQueue()
            await q.put(1)
            await q.put(2)
            x = await q.get_all()
            self.assertEqual([1, 2], x)
            self.assertEqual(0, q.qsize())

            # Will block until something is put in place
            # We need to set up some async puts and waits to test this
            evt = asyncio.Event()
            evt2 = asyncio.Event()

            async def _put():
                await evt.wait()
                await q.put("foo")

            async def _wait():
                self.assertEqual(["foo"], await q.get_all())
                evt2.set()

            asyncio.create_task(_put())
            asyncio.create_task(_wait())
            evt.set()
            await evt2.wait()

        asyncio.get_event_loop().run_until_complete(_t())

    def test_put_all(self):
        async def _t():
            q = AdvancedAsyncQueue()

            # Add empty list
            await q.put_all([])
            self.assertEqual(0, q.qsize())

            await q.put_all(["foo"])
            self.assertEqual(1, q.qsize())
            self.assertEqual(["foo"], await q.get_all())

            await q.put_all(["foo", "bar"])
            self.assertEqual(2, q.qsize())
            self.assertEqual(["foo", "bar"], await q.get_all())

        asyncio.get_event_loop().run_until_complete(_t())

    def test_get_all_if_any(self):
        async def _t():
            q = AdvancedAsyncQueue()

            # Empty list returns immediately
            self.assertEqual([], await q.get_all_if_any())

            await q.put("foo")
            self.assertEqual(["foo"], await q.get_all_if_any())

            await q.put("foo")
            await q.put("bar")
            self.assertEqual(["foo", "bar"], await q.get_all_if_any())

        asyncio.get_event_loop().run_until_complete(_t())
