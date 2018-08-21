#!/usr/bin/env python3
"""
Handy class for consuming websockets as a client.

Source: https://github.com/rharder/handy

August 2018 - Initial creation
"""
from typing import AsyncIterator

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"

import asyncio

import aiohttp

# testing
WEBSOCKET_URL = 'wss://stream.pushbullet.com/websocket/'


def main():
    url = "wss://demos.kaazing.com/echo"
    url = "ws://localhost:9990/rnd"
    proxy = None
    proxy = ""
    key = ""
    url = WEBSOCKET_URL + key

    #
    async def _run():

        headers = {"Access-Token": key}
        print(headers)
        async with WebsocketClient(url, proxy=proxy, headers=headers, verify_ssl=False) as wc:

            # print("Sending: hello")
            # await wc.send_str("hello")
            #
            #             # print("Sending: world")
            #             # await wc.send_str("world")
            #
            #             # print("Flushing...")
            #             # await wc.flush_incoming(timeout=1)
            #             # print("\tFlushed.")
            #
            #             # print("Sending: foobar")
            #             # await wc.send_str("foobar")
            #
            #             # msg = await wc.get_msg()
            #             # print("Received:", msg)
            #             # try:
            #             #     msg = await wc.get_msg(timeout=1)
            #             # except asyncio.futures.TimeoutError as te:
            #             #     print("Timeout:", te)
            #             # else:
            #             #     print("Received:", msg)
            #
            #             # while True:
            #             #     try:
            #             #         msg = await wc.get_msg(timeout=9999)
            #             #         print("Received:", msg)
            #             #     except Exception as ex:
            #             #         print("get_msg got an error", ex)
            #             #         break
            #
            counter = 0
            async for msg in wc:
                counter += 1
                print("Received message:", msg)
                if counter > 44:
                    await wc.close()

            print("for block exited")
        print("with block exited")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_run())


class WebsocketClient():
    """A handy class for consuming websockets as a client.


    Source: https://github.com/rharder/handy
    Author: Robert Harder
    License: Public Domain

    """

    def __init__(self, url, headers=None, verify_ssl=None, proxy=None, session=None):
        self.url = url
        self.headers = headers
        self.verify_ssl = verify_ssl
        self.proxy = proxy
        self._session = session  # type: aiohttp.ClientSession
        self._socket = None  # type: aiohttp.ClientWebSocketResponse
        self._queue = None  # type: asyncio.Queue

    async def _create_session(self) -> aiohttp.ClientSession:
        aio_connector = None  # type: aiohttp.TCPConnector
        if self.verify_ssl is not None and self.verify_ssl is False:
            aio_connector = aiohttp.TCPConnector(ssl=False, loop=asyncio.get_event_loop())
        session = aiohttp.ClientSession(headers=self.headers, connector=aio_connector)
        return session

    async def close(self):
        await self._socket.close()
        # self._socket = None
        await self._session.close()
        # self._session = None

    @property
    def closed(self):
        return self._socket.closed

    async def send_str(self, data):
        """Sends a string to the websocket server."""
        await self._socket.send_str(data)
        await asyncio.sleep(0)

    async def send_bytes(self, data):
        """Sends raw bytes to the websocket server."""
        await self._socket.send_bytes(data)
        await asyncio.sleep(0)

    async def send_json(self, data):
        """Sends a json message to the websocket server."""
        await self._socket.send_json(data)
        await asyncio.sleep(0)

    async def flush_incoming(self, timeout=0):
        """Flushes all messages received to date but not yet processed.

        The method will return silently if the timeout period is reached.

        :param int timeout: the timeout in seconds
        """

        async def _flush_all():
            while True:
                _ = await self._queue.get()
                await asyncio.sleep(0)

        try:
            await asyncio.wait_for(_flush_all(), timeout=timeout)
        except asyncio.futures.TimeoutError:
            pass

    async def get_msg(self, timeout: int = None) -> aiohttp.WSMessage:
        """Returns the next message from the websocket server.

         This method may throw a StopAsyncIteration exception if the socket
         closes or another similar event occurs.

         If a timeout is specified, this method may throw an
         asyncio.futures.TimeoutError (not the builtin version) if the timeout
         period is exceeded without a message being available from the server.
         """
        if timeout is None:
            msg = await self._queue.get()
            if type(msg) == StopAsyncIteration:
                raise msg
            return msg
        else:
            msg = await asyncio.wait_for(self.get_msg(), timeout=timeout)
            return msg

    async def __aenter__(self):
        self._queue = asyncio.Queue()
        self._session = self._session or await self._create_session()
        self._socket = await self._session.ws_connect(self.url, proxy=self.proxy)

        async def _listen_for_messages():
            try:

                # Spend time here waiting for incoming messages
                async for msg in self._socket:  # type: aiohttp.WSMessage
                    await self._queue.put(msg)
                    await asyncio.sleep(0)

            except Exception as e:
                sai = StopAsyncIteration(e)
                await self._queue.put(sai)
            else:
                sai = StopAsyncIteration()
                await self._queue.put(sai)

        asyncio.create_task(_listen_for_messages())
        await asyncio.sleep(0)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.close()

    def __aiter__(self) -> AsyncIterator[aiohttp.WSMessage]:
        return self

    async def __anext__(self) -> aiohttp.WSMessage:
        if self._socket.closed:
            raise StopAsyncIteration("The websocket has closed.")

        try:
            msg = await self._queue.get()
        except Exception as e:
            raise StopAsyncIteration(e)

        if type(msg) == StopAsyncIteration:
            raise msg

        return msg


if __name__ == "__main__":
    main()
