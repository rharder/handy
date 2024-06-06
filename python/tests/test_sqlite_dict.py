#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from unittest import TestCase

from handy.sqlite_dict import SqliteDict


class TestSqliteDict(TestCase):

    def test_get_set(self):
        filename = "sqlite_dict_test.sqlite3"
        # Path(filename).unlink(missing_ok=True)
        fd = SqliteDict(filename)  # , {"a": "b"})

        # Check emptiness
        fd.drop_tables()
        self.assertEqual(0, len(fd))
        self.assertEqual(0, len(fd.items()))
        self.assertIsNone(fd.get("foobar"))

        # Set/Get some basics
        self.assertNotIn("a", fd)
        self.assertIsNone(fd.get("a"))
        self.assertEqual("foo", fd.get("a", "foo"))
        fd["a"] = "alpha"
        self.assertIn("a", fd)
        self.assertEqual("alpha", fd["a"])
        self.assertEqual("alpha", fd.get("a", "foo"))
        self.assertEqual(1, len(fd))

        self.assertNotIn("b", fd)
        fd["b"] = "bravo"
        self.assertIn("a", fd)
        self.assertIn("b", fd)
        self.assertEqual("bravo", fd["b"])
        self.assertEqual(2, len(fd))
        self.assertEqual(["a", "b"], list(fd.keys()))

        for k, v in fd.items():
            self.assertIn(k, ["a", "b"])
            self.assertIn(v, ["alpha", "bravo"])

    def test_delete(self):
        filename = "sqlite_dict_test.sqlite3"
        # Path(filename).unlink(missing_ok=True)
        fd = SqliteDict(filename)
        fd.drop_tables()

        self.assertEqual(0, len(fd))
        self.assertNotIn("a", fd)
        with self.assertRaises(KeyError):
            del fd["a"]

        fd["a"] = "alpha"
        self.assertEqual(1, len(fd))
        self.assertIn("a", fd)
        del fd["a"]
        self.assertEqual(0, len(fd))
        self.assertNotIn("a", fd)

        fd["a"] = "alpha"
        fd["b"] = "bravo"
        self.assertEqual(2, len(fd))
        self.assertIn("a", fd)
        self.assertIn("b", fd)
        del fd["a"]
        self.assertEqual(1, len(fd))
        self.assertNotIn("a", fd)
        self.assertIn("b", fd)
        del fd["b"]
        self.assertEqual(0, len(fd))

    def test_types(self):
        filename = "sqlite_dict_test.sqlite3"
        # Path(filename).unlink(missing_ok=True)
        fd = SqliteDict(filename)
        fd.drop_tables()
        self.assertEqual(0, len(fd))

        fd[1] = "one"
        self.assertIn(1, fd)
        self.assertIn("1", fd)
        self.assertEqual("one", fd[1])
        self.assertEqual("one", fd["1"])

        dict_val = {"a": "alpha", "b": "bravo"}
        fd["d"] = dict_val
        self.assertEqual(dict_val, fd["d"])

        needs_pickling = {"a": "alpha", "t": datetime.now()}
        fd["p"] = needs_pickling
        self.assertEqual(needs_pickling, fd["p"])
        self.assertEqual(needs_pickling["t"], fd["p"]["t"])

    def test_update(self):
        filename = "sqlite_dict_test.sqlite3"
        # Path(filename).unlink(missing_ok=True)
        fd = SqliteDict(filename)
        fd.drop_tables()
        self.assertEqual(0, len(fd))

        d = {"a": "alpha", "b": "bravo"}
        fd.update(d)
        self.assertEqual(2, len(fd))
        self.assertIn("a", fd)
        self.assertIn("b", fd)

    def test_table_names(self):
        filename = "sqlite_dict_test.sqlite3"
        # Path(filename).unlink(missing_ok=True)
        fda1 = SqliteDict(filename, table_name="table_a")
        fda2 = SqliteDict(filename, table_name="table_a")
        fdb = SqliteDict(filename, table_name="table_b")

        fda1.drop_tables()
        fdb.drop_tables()
        self.assertEqual(0, len(fda1))
        self.assertEqual(0, len(fda2))
        self.assertEqual(0, len(fdb))

        fda1["a"] = "alpha"
        self.assertIn("a", fda1)
        self.assertIn("a", fda2)
        self.assertNotIn("a", fdb)
        fdb["b"] = "bravo"
        self.assertNotIn("b", fda1)
        self.assertNotIn("b", fda2)
        self.assertIn("b", fdb)
