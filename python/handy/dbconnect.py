# -*- coding: utf-8 -*-
import sqlite3

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__date__ = "5 Dec 2016"
__license__ = "Public Domain"
__homepage__ = "https://github.com/rharder/handy"


class DbConnect():
    """ Context manager to handle opening log file, ensuring table exists, and closing afterward. """

    def __init__(self, filename):
        self.filename = filename
        self.connection = None

    def __enter__(self):
        """
        :rtype: sqlite3.Cursor
        """
        import sqlite3
        self.connection = sqlite3.connect(self.filename)
        return self.connection  # .cursor()

    def __exit__(self, type, value, traceback):
        self.connection.commit()
        self.connection.close()

"""
Simpler like this:

    @contextmanager
    def connection(self):
        _conn = sqlite3.connect(self.path)
        try:
            yield _conn
        finally:
            _conn.close()

"""