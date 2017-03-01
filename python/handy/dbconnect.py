import sqlite3

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
