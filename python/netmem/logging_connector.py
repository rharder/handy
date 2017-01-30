import logging

from .connector import Connector


class LoggingConnector(Connector):
    """
    Trivial connector that only logs messages as they are sent.
    """

    def __init__(self):
        super().__init__()
        self.log.setLevel(logging.DEBUG)

    def connect(self, listener):
        super().connect(listener)
        self.log.info("Connected.")
        self.listener.connection_made(self)

    def send_message(self, msg: dict):
        self.log.info("Sending message: {}".format(msg))
