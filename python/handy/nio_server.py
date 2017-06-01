"""
Provides an easy-to-subclass Nonblocking network server using asyncio and coroutines.
Source: https://github.com/rharder/handy
"""
import asyncio
import sys
from abc import ABCMeta, abstractmethod

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"

class NonblockingServer(metaclass=ABCMeta):
    """
    Nonblocking Server class to aid in the mechanics.
    To use, subclass and override the handle_connection and handle_exception functions.
    """

    def __init__(self,
                 port: int = 8000,
                 host: str = None,
                 connection_timeout: float = None,
                 verbosity: int = 0):
                 # loop: asyncio.AbstractEventLoop = None):
        """
        Creates a new Nonblocking Server.

        :param int port: The TCP port on which to listen
        :param str host: The host (for mulit-nic machines mostly)
        :param float connection_timeout: Timeout before a connection is dropped
        :param int verbosity: increase verbosity, 0=default=quiet
        """
        self.verbosity = verbosity

        self.port = port
        self.host = host
        self.connection_timeout = connection_timeout
        # self.__loop = loop
        self.__server_running = False


    def __str__(self):
        return "{klass}({host}:{port})".format(
                klass=self.__class__.__name__, port=self.port, host=self.host)
    #
    # @property
    # def port(self) -> int:
    #     return self.__port
    #
    # @port.setter
    # def port(self, port: int):
    #     """
    #     Set the port on which to connect.  Raises an exception if server is already running.
    #     :param int port:
    #     """
    #     if self.__server_running:
    #         raise Exception("Cannot change port after server is started.")
    #     self.__port = port
    #
    # @property
    # def host(self) -> str:
    #     return self.__host
    #
    # @host.setter
    # def host(self, host: str):
    #     """
    #     Set the host with which to bind when listening.  Raises an exception if server is already running.
    #     :param str host:
    #     :return:
    #     """
    #     if self.__server_running:
    #         raise Exception("Cannot change bound host after server is started.")
    #     self.__host = host
    #
    # @property
    # def connection_timeout(self):
    #     return self.__connection_timeout
    #
    # @connection_timeout.setter
    # def connection_timeout(self, connection_timeout):
    #     self.__connection_timeout = connection_timeout

    # @property
    # def loop(self):
    #     return self.__loop
    #
    # @loop.setter
    # def loop(self, loop: asyncio.AbstractEventLoop):
    #     self.__loop = loop

    def start_listening(self, loop: asyncio.AbstractEventLoop=None):
        """
        Attaches the server to an existing event loop, which presumably will later have
        loop.run_forever() called with other things attached to it.

        :param asyncio.AbstractEventLoop loop: the loop to attach
        """
        # loop.run_until_complete(self.__listen_for_connection())
        loop = loop or asyncio.get_event_loop()
        loop.create_task(self.__listen_for_connection())
        self.loop = loop

    def run_forever(self, loop: asyncio.AbstractEventLoop = None):
        """
        Creates an event loop and runs the server forever.
        :param asyncio.AbstractEventLoop loop: the event loop to use
        """
        loop = loop or asyncio.get_event_loop()
        self.start_listening(loop)

        def wakeup():
            """Needed for Windows to notice Ctrl-C and other signals"""
            loop.call_later(0.1, wakeup)

        loop.call_later(0.1, wakeup)

        loop.run_forever()

    @asyncio.coroutine
    def __listen_for_connection(self):
        """ Listens for a new TCP connection and then hands it off to __handle_connection. """
        self.__server_running = True
        yield from asyncio.start_server(self.__handle_connection,
                                        host=self.host,
                                        port=self.port)
        self.__server_running = False

    @asyncio.coroutine
    def __handle_connection(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        """
        Handle new TCP connection.

        This function only determines the initial Raptor command and then hands off control
        to an appropriate handler.  The only known Raptor commands at this time are DIRECTORY,
        which gives Raptor a list of known test cases, or the name of a test to try loading.

        :param asyncio.StreamReader client_reader: Associated input stream
        :param asyncio.StreamWriter client_writer: Associated output stream
        """
        # http://www.drdobbs.com/open-source/the-new-asyncio-in-python-34-servers-pro/240168408

        # This timeout handling feels awkward.  I want to wrap EVERYTHING in a timeout.
        # To do this, I need to catch a TimeoutError NOT wrapping the asyncio.wait_for() function
        # directly but rather from the calling context.  In other words, try/except goes around
        # the wrap_timeout_outer() call, but it's _within_ the wrap_timeout_outer() function
        # where we actually have the asyncio.wait_for() function.  The wait_for() function in
        # turn calls the wrap_timeout_inner() function, which actually does the work.

        user_dict = {}

        @asyncio.coroutine
        def wrap_timeout_outer():
            """ One line wrapper """
            if self.connection_timeout is None:
                yield from self.handle_connection(client_reader, client_writer, user_dict)  # Subclasses override this
            else:
                @asyncio.coroutine
                def wrap_timeout_inner():
                    yield from self.handle_connection(client_reader, client_writer, user_dict)

                yield from asyncio.wait_for(wrap_timeout_inner(), self.connection_timeout)

        try:
            # MAIN PROCESSING ENTERS HERE
            yield from wrap_timeout_outer()
        except Exception as e:
            if self.verbosity >= 10:
                print("Caught exception. Will pass to exception callback handler {}.".format(self.handle_exception), e,
                      file=sys.stderr)
            yield from self.handle_exception(e, client_reader, client_writer, user_dict)  # Subclasses override this

        finally:
            if self.verbosity >= 10:
                print("Closing connection")
            try:
                yield from client_writer.drain()
            except Exception as e:
                pass
            try:
                client_writer.close()
            except Exception as e:
                print("error closing", file=sys.stderr)
                pass

    # @abstractmethod
    @asyncio.coroutine
    def handle_connection(self, client_reader: asyncio.StreamReader,
                          client_writer: asyncio.StreamWriter, user_dict: dict):
        """
        Override this function in your subclass to handle a new incoming connection.

        To read from the client_reader, be sure to wrap the read command in a shield like so:

        from_client = yield from asyncio.shield(client_reader.readline())

        When the function exits, the connection will be closed.

        :param asyncio.StreamReader client_reader: stream for reading incoming data
        :param asyncio.StreamWriter client_writer: stream for sending outgoing data
        :param dict user_dict: optional user dictionary you can use to pass data among callbacks
        """
        pass

    # @abstractmethod
    @asyncio.coroutine
    def handle_exception(self,
                         exc: Exception,
                         client_reader: asyncio.StreamReader,
                         client_writer: asyncio.StreamWriter,
                         user_dict: dict):
        """
        Override this function to handle exceptions.  You can pass context data from your handle_connection
        function using the user dictionary user_dict.

        When the function exits, the connection will be closed.

        :param Exception exc: the exception that was caught
        :param asyncio.StreamReader client_reader: stream for reading incoming data
        :param asyncio.StreamWriter client_writer: stream for sending outgoing data
        :param dict user_dict: optional user dictionary you can use to pass data among callbacks
        """
        raise exc


class ExampleLineEchoNonblockingServer(NonblockingServer):
    """
    Example of a NonblockingServer subclass that echos lines sent to it.
    """
    ENCODING = 'utf-8'

    def __str__(self):
        return "{}, encoding={}".format(super().__str__(), ExampleLineEchoNonblockingServer.ENCODING)

    @asyncio.coroutine
    def handle_connection(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter,
                          user_dict: dict):
        """
        Example of how to handle a new connection.
        """
        client_writer.write('Greetings.  Lines will be echoed back to you.  Type EOF to exit.\n'
                            .encode(ExampleLineEchoNonblockingServer.ENCODING))
        yield from client_writer.drain()  # Non-blocking

        from_client = None
        while from_client != 'EOF':
            # Discussion: I think it might be a bug (or "feature") in the Python 3.4.3 I'm developing on
            # that there is not a proper error thrown with this readline or the following write.
            # There's a note here: https://github.com/aaugustin/websockets/issues/23
            # In any event, wrapping the read in an asyncio.async(..) solves the problem.
            # Without async(..) when a connection is dropped externally, the code goes into an infinite loop
            # reading an empty string b'' and then writing with the should-be-exception getting swallowed
            # somewhere inside Python's codebase.
            # from_client = yield from client_reader.readline()  # This should be OK, but it's not, strangely
            # from_client = yield from asyncio.shield(client_reader.readline())  # Also works

            from_client = yield from asyncio.async(client_reader.readline())  # Use this instead

            from_client = from_client.decode('utf-8').strip()
            print("Recvd: [{}]".format(from_client))

            client_writer.write("{}\n".format(from_client).encode(ExampleLineEchoNonblockingServer.ENCODING))
            yield from client_writer.drain()  # Non-blocking

    @asyncio.coroutine
    def handle_exception(self, exc: Exception, client_reader: asyncio.StreamWriter, client_writer: asyncio.StreamWriter,
                         user_dict: dict):

        if type(exc) is asyncio.TimeoutError:
            print('Timed out.', 'User dict: ', user_dict, "Error: ", exc, file=sys.stderr)
        elif type(exc) is ConnectionResetError:
            print('Connection reset.', 'User dict: ', user_dict, "Error: ", exc, file=sys.stderr)
        else:
            print("Exception: {}".format(type(exc)), 'User dict: ', user_dict, "Error: ", exc, file=sys.stderr)

    @staticmethod
    def main(ex: int = 1):
        """
        Example usage of the non blocking server.
        :param int ex: Example number (1 or 2, default is 1)
        :return:
        """

        if ex == 1:
            # Example 1
            server = ExampleLineEchoNonblockingServer(port=8000, verbosity=1)
            print(server)
            server.run_forever()
            # Comment above lines to run Example 2 below
        elif ex == 2:
            # Example 2
            server1 = ExampleLineEchoNonblockingServer(port=8001, verbosity=1)
            server2 = ExampleLineEchoNonblockingServer(port=8002, verbosity=1)
            print(server1)
            print(server2)
            loop = asyncio.get_event_loop()
            server1.start_listening(loop)
            server2.start_listening(loop)
            loop.run_forever()
        else:
            print("Unknown example number ({}). Try 1 or 2.".format(ex))


def main():
    """
    Example usage of the non blocking server
    :param ex:
    :return:
    """
    print(__doc__)
    if len(sys.argv) > 1:
        ex = int(sys.argv[1])
    else:
        ex = 1

    ExampleLineEchoNonblockingServer.main(ex)


if __name__ == "__main__":  # while debugging
    main()
