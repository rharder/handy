#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A sqlite3-backed dictionary.
"""
import json
import logging
import os
import pickle
import sqlite3
import string
import time
from collections import UserDict
from contextlib import contextmanager
from pathlib import Path

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"
__homepage__ = "https://github.com/rharder/handy"

from pprint import pprint

from typing import Union

logger = logging.getLogger(__name__)


def example():
    logging.basicConfig(level=logging.DEBUG)
    filename = "example.sqlite3"
    # filename = None
    x = {"a": "b"}
    fd = SqliteDict(filename)  # , {"a": "b"})
    fd.drop_tables()
    # fd.reload_before_read = True
    fd.update({1: 1, 2: 2, "x": "y"}, )
    print("length", len(fd))
    pprint(fd)
    print("foobar in?", "foobar" in fd)

    print("setting a:b")
    fd["a"] = "b"
    pprint(fd)
    print("deleting a")
    del fd["a"]
    pprint(fd)

    print("reading db...")
    fd2 = SqliteDict(filename)
    pprint(fd2)

    # fd = FileDict()
    # fd.filename = filename
    # fd.reload(filename)

    # print("fd", fd)
    # fd["hello"] = "world"
    # print("fd", fd)
    # print("fd['a'] = ", fd['a'])

    # fd["b"] = "c"
    # with fd:
    #     fd["c"] = "c"
    #     fd["d"] = "d"
    # filename = "example.json"
    # fd.force_save(filename)
    # with exclusive_open(filename) as f:
    #     print(f"{filename} CONTENTS: ", f.read())
    # pprint(fd)


class SqliteDict(UserDict):
    TABLE_NAME_DEFAULT = "dict"
    CREATE_TABLES = [
        """CREATE TABLE IF NOT EXISTS {table_name} (
            k   VARCHAR(500) PRIMARY KEY,
            v   BLOB,
            class TEXT
            );""",
    ]

    def __init__(self, filename: Union[str, bytes, os.PathLike] = None,
                 *kargs,
                 table_name: str = None,
                 read_only: bool = None,
                 **kwargs,
                 ):
        super().__init__(*kargs, **kwargs)
        # super().__init__()
        self.sqlite_file: Union[str, bytes, os.PathLike] = filename
        self.read_only: bool = read_only
        self._current_connection = None
        if self.sqlite_file is None:
            self.sqlite_file = ":memory:"
            logger.warning(f"No filename provided for sqlite file - using :memory: database instead")
        self.force_pickle = False

        # self._suspend_save: bool = True
        # self._reload_before_read: bool = False
        self._table_name: str = SqliteDict.TABLE_NAME_DEFAULT
        self.table_name = table_name  # Now use setter

        _elements_received_in_constructor: bool = len(self) > 0

    def __str__(self):
        return super().__str__() + f", file={self.sqlite_file}"

    # def __repr__(self):
    #     return self.__str__() + \
    #            f"(Records={self.count_records():,}"
    @property
    def table_name(self) -> str:
        return self._table_name

    @table_name.setter
    def table_name(self, val):
        """Sets the name of the table used for metadata storage.
        The name is sanitized to avoid SQL injection attacks."""
        if val is None:
            self._table_name = self.TABLE_NAME_DEFAULT
        else:
            # Need to sanitize against SQL injection attack
            allowable = set(string.ascii_letters + "_")
            val = "".join(filter(lambda x: x in allowable, str(val)))
            self._table_name = str(val)

    @contextmanager
    def connection(self, ensure_tables=True):
        # This helps with re-entrancy if we have with db.connection() holding open a connection
        if self._current_connection:
            yield self._current_connection
            return

        # Protect against nested calls and multithreaded calls.
        # My Comp Sci sensibilities don't like it, but it's working for now.
        while self._current_connection is not None:
            time.sleep(0.01)

        if self.read_only:
            _conn = sqlite3.connect(f"file:{self.sqlite_file}?mode=ro", uri=True)
        else:
            try:
                _conn = sqlite3.connect(self.sqlite_file)
            except sqlite3.OperationalError as ex:
                # first try "touch"
                # If we create it this way, we're good to go
                Path(self.sqlite_file).touch(exist_ok=True)
                _conn = sqlite3.connect(self.sqlite_file)

        if ensure_tables:
            self._ensure_tables(_conn)
        try:
            self._current_connection = _conn
            yield _conn
        finally:
            # If we are dealing with a :memory: db, then we don't really ever want to close the connection
            if self.sqlite_file != ":memory:":
                _conn.close()
                self._current_connection = None

    def drop_tables(self):

        with self.connection(ensure_tables=False) as conn:
            c = conn.cursor()
            logger.debug(f"Dropping table {self.table_name} ...")
            c.execute(f"DROP TABLE IF EXISTS {self.table_name};")
            conn.commit()

            c = conn.cursor()
            c.execute("VACUUM;")
            conn.commit()

    def _ensure_tables(self, conn):
        c = conn.cursor()
        missing_tables = False
        for table_name in (self.table_name,):
            c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            if not c.fetchall():
                missing_tables = True
                break

        if missing_tables:
            self._create_tables(conn)

    def _create_tables(self, conn):
        c = conn.cursor()
        for sql in self.CREATE_TABLES:
            sql_formatted = sql.format(
                table_name=self.table_name)
            c.execute(sql_formatted)
        conn.commit()

    def verify(self):
        """Verifies that the tables exist in the database."""
        with self.connection() as conn:
            self._ensure_tables(conn)

    def compact(self):
        """Executes the SQL VACUUM command to compact the database
        (mostly useful after many deletions)."""
        with self.connection(ensure_tables=False) as conn:
            c = conn.cursor()
            c.execute("VACUUM;")
            conn.commit()

    def __contains__(self, item):
        with self.connection() as conn:
            c = conn.cursor()
            try:
                c.execute(f"SELECT k FROM {self.table_name} WHERE k = ?;", (item,))
                return c.fetchone() is not None
            except Exception as ex:
                logger.debug(f"Failed to retrieve key={item}: {ex}")

    def __len__(self):
        with self.connection() as conn:
            c = conn.cursor()
            try:
                c.execute(f"SELECT COUNT(k) FROM {self.table_name};")
                return c.fetchone()[0]
            except Exception as ex:
                logger.debug(f"Failed to count rows: {ex}")
        return 0

    def __iter__(self):
        with self.connection() as conn:
            c = conn.cursor()
            c.execute(f"SELECT k from {self.table_name}")
            for row in c.fetchall():
                yield row[0]

    def __delitem__(self, key):
        with self.connection() as conn:
            c = conn.cursor()
            c.execute(f"DELETE FROM {self.table_name} where k = ? ;", (key,))
            conn.commit()
            if c.rowcount == 0:
                raise KeyError(f"Key not found, __delitem__: {key}")

    def __getitem__(self, key):
        with self.connection() as conn:
            c = conn.cursor()
            c.execute(f"SELECT v, class FROM {self.table_name} WHERE k = ?;", (key,))
            result = c.fetchone()
            if result:
                v = result[0]
                c = result[1]
                if c == "int":
                    val = int(v)
                elif c == "float":
                    val = float(v)
                elif c == "json":
                    val = json.loads(v)
                elif c == "pickle":
                    # val = pickle.loads(base64.b64decode(v))
                    val = pickle.loads(v)
                else:
                    val = v
            else:
                raise KeyError(f"Key not found, __get__: {key}")
        return val

    def __setitem__(self, key, value):
        with self.connection() as conn:
            success = False
            # Update the "meta" table
            if not self.force_pickle:
                try:
                    c = conn.cursor()
                    c.execute(
                        f"REPLACE INTO {self.table_name} (k, v, class) VALUES (?, ?, ?); ",
                        (key, value, value.__class__.__name__ if value else None))
                    conn.commit()
                    c.close()
                    success = True
                except Exception as ex:
                    # It might just be an unsupported data type, in which case we'll try json or pickling it instead
                    logger.debug(f"Could not save - might not be native data type, ok, will try pickling: {ex}, "
                                 f"key={key}, value={value}")
                    success = False
            if not success:
                if self.force_pickle:
                    # encoded, encoded_type = base64.b64encode(pickle.dumps(value)), "pickle"
                    encoded, encoded_type = pickle.dumps(value), "pickle"
                else:
                    try:
                        encoded, encoded_type = json.dumps(value, indent=2), "json"
                    except Exception as ex:
                        # encoded, encoded_type = base64.b64encode(pickle.dumps(value)), "pickle"
                        encoded, encoded_type = pickle.dumps(value), "pickle"

                c = conn.cursor()
                c.execute(
                    f"REPLACE INTO {self.table_name} (k, v, class) VALUES (?, ?, ?); ",
                    (key, encoded, encoded_type))
                conn.commit()
                c.close()
                logger.debug(f"Saved key={key}, value={value} ({encoded_type})")
                return True
            else:
                logger.debug(f"Saved key={key}, value={value}")
                return True


if __name__ == '__main__':
    example()
