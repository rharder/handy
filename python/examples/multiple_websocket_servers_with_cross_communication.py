#!/usr/bin/env python3
"""
Illustrates how to have multiple websocket servers running and send
messages to all their various clients at once.

In response to stackoverflow question:
http://stackoverflow.com/questions/35820782/how-to-manage-websockets-across-multiple-servers-workers

Pastebin: http://pastebin.com/xDSACmdV

Still working on aiohttp v3.3 changes - June 2018
"""
import asyncio
import datetime
import random
import time
import webbrowser

import aiohttp
from aiohttp import web

from handy.websocket_server import WsServer

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


def main():
    # Create servers
    cap_srv = CapitalizeEchoServer(port=9990)
    cap_srv2 = CapitalizeEchoServer(port=9990, route="/lower", transform=str.lower)
    # rnd_srv = RandomQuoteServer(port=9991, interval=2)
    # tim_srv = TimeOfDayServer(port=9992)

    # Queue their start operation
    loop = asyncio.get_event_loop()
    loop.create_task(cap_srv.start())
    loop.create_task(cap_srv2.start())
    # loop.create_task(rnd_srv.start())
    # loop.create_task(tim_srv.start())

    # Open web pages to test them
    # webtests = [9990, 9991, 9992]
    webtests = [9990]
    for port in webtests:
        url = "http://www.websocket.org/echo.html?location=ws://localhost:{}".format(port)
        webbrowser.open(url)
    print("Be sure to click 'Connect' on the webpages that just opened.")

    # Queue a simulated broadcast-to-all message
    async def _alert_all(msg, delay=0):
        await asyncio.sleep(delay)
        print("Sending alert:", msg)
        msg_dict = {"alert": str(msg)}
        await cap_srv.broadcast_json(msg_dict)
        # await rnd_srv.broadcast_json(msg_dict)
        # await tim_srv.broadcast_json(msg_dict)

    loop.create_task(_alert_all("all your base are belong to us", 5))

    # Run event loop
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("keyboard interrupt")
        loop.run_until_complete(cap_srv.close())
        loop.run_until_complete(rnd_srv.close())
        loop.run_until_complete(tim_srv.close())

        loop.close()
    print("loop.run_forever() must have finished")


class CapitalizeEchoServer(WsServer):
    """ Echoes back to client whatever they sent, but capitalized. """

    def __init__(self, transform=str.upper, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.transform = transform

    async def on_websocket(self, ws: web.WebSocketResponse):
        """Identify the demo server"""
        await ws.send_str("Connected to demo {}".format(self.__class__.__name__))
        await super().on_websocket(ws)

    async def on_message(self, ws: web.WebSocketResponse, ws_msg_from_client: aiohttp.WSMessage):
        if ws_msg_from_client.type == web.WSMsgType.TEXT:
            # cap = str(ws_msg_from_client.data).upper()
            cap = self.transform(str(ws_msg_from_client.data))
            await ws.send_str(cap)


class RandomQuoteServer(WsServer):
    """ Sends a random quote to the client every so many seconds. """
    QUOTES = ["Wherever you go, there you are.",
              "80% of all statistics are made up.",
              "If a tree falls in the woods, and no one is around to hear it, does it make a noise?"]

    def __init__(self, interval: float = 10, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.interval = interval

    async def on_websocket(self, ws: web.WebSocketResponse):
        """
        Override this function if you want to handle new incoming websocket clients.
        The default behavior is to listen indefinitely for incoming messages from clients
        and call on_message() with each one.
        """
        await ws.send_str("Connected to demo {}".format(self.__class__.__name__))

        async def _regular_interval():
            # counter = 0
            while not ws.closed:
                quote = random.choice(self.QUOTES)
                await ws.send_json({"quote": quote})
                await asyncio.sleep(self.interval)
            # print("Exiting _regular_interval...")

        asyncio.create_task(_regular_interval())
        await super().on_websocket(ws)  # Block here until socket dies

        # print("on_websocket last line within RandomQuoteServer", self)


class TimeOfDayServer(WsServer):
    """ Sends a message to all clients simultaneously about time of day. """

    def __init__(self, interval: float = 2, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.interval = interval
        # self.task = None  # type: asyncio.Task

    async def start(self, *kargs, **kwargs):
        await super().start(*kargs, **kwargs)

        async def _regular_interval():
            # counter = 0
            while self.running and not self.shutting_down:
                # if counter >= 5:
                #     await self.close()
                #     print("closed myself", self)
                #     break
                if int(time.time()) % self.interval == 0:  # Only on the x second mark
                    timestamp = "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())
                    await self.broadcast_json({"timestamp": timestamp})
                    # counter += 1
                await asyncio.sleep(1)

        # self.task = asyncio.create_task(_regular_interval())
        asyncio.create_task(_regular_interval())

    async def close(self):
        # self.task.cancel()
        await super().close()


if __name__ == "__main__":
    main()
