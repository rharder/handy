import logging

import asyncio


class Connector(object):
    def __init__(self):
        """
        receive message will be called thus: self.receive_message(self, data)
        and should be defined thus: def receive_message(self, connector, data)
        """
        # self.net_mem = None  # type: netmem.NetworkMemoryC
        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.listener = None  # type: ConnectorListener

    def connect(self, listener, loop: asyncio.BaseEventLoop = None):
        """
        Called by the NetworkMemory object when its own connect() function is called.

        Sub classes should be sure to invoke this method before continuing
        with their own connect routines:

        def connect(self, listener)
            super().connect(listener)
            ...  # go on about your business

            return self  # Always return self

        :param listener:
        :return: self
        """
        self.listener = listener
        self.loop = loop or asyncio.get_event_loop()
        return self

    def send_message(self, msg: dict):
        """ Instructs this Connector to send an update message by whatever means. """
        pass

    def close(self):
        """ Provides an opportunity for the Connector to gracefully close. """
        pass


class ConnectorListener(object):
    """ Used more like a Java interface so that connectors know
    what methods to use for callbacks to NetworkMemory. """

    def message_received(self, connector: Connector, msg: dict):
        pass

    def connection_made(self, connector: Connector):
        pass

    def connection_lost(self, connector: Connector, exc=None):
        pass

    def connection_error(self, connector: Connector, exc=None):
        pass
