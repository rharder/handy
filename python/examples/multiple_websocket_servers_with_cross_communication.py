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
import sys
import time
import traceback
import webbrowser

import aiohttp
from aiohttp import web
sys.path.append("..")
from handy.websocket_server import WebsocketHandler, WebServer

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


def main():
    # Create servers
    server = WebServer(port=9990)
    cap_hndlr = CapitalizeEchoHandler()
    rnd_hndlr = RandomQuoteHandler(interval=2)
    tim_hndlr = TimeOfDayHandler()

    server.add_get_route("/cap", cap_hndlr)
    server.add_get_route("/rnd", rnd_hndlr)
    server.add_get_route("/time", tim_hndlr)

    # Queue their start operation
    loop: asyncio.BaseEventLoop
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()  # Processes
        asyncio.get_child_watcher()  # Main loop
    
    asyncio.set_event_loop(loop)
    loop = asyncio.get_event_loop()
    loop.create_task(server.start())
    # loop.create_task(server.start())

    # Open web pages to test them
    # webtests = [9990, 9991, 9992]
    webtests = [9990]
    for port in webtests:
        url = "http://www.websocket.org/echo.html?location=ws://localhost:{}/cap".format(port)
        webbrowser.open(url)
    print("Be sure to click 'Connect' on the webpages that just opened.")

    # Queue a simulated broadcast-to-all message
    async def _alert_all(msg, delay=0, num=1):
        for _ in range(num, 0, -1):
            await asyncio.sleep(delay)
            # print("Alert loop:", id(asyncio.get_event_loop()))
            print("Broadcasting alert:", msg)
            msg_dict = {"alert": str(msg)}
            await cap_hndlr.broadcast_json(msg_dict)
            await rnd_hndlr.broadcast_json(msg_dict)
            await tim_hndlr.broadcast_json(msg_dict)

        # await server.close()
        # print("alert coroutine closed server and is exiting")

    loop.create_task(_alert_all("all your base are belong to us", 5))

    # Run event loop
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("keyboard interrupt")
        loop.run_until_complete(server.shutdown())

        loop.close()
    print("loop.run_forever() must have finished")


class CapitalizeEchoHandler(WebsocketHandler):
    """ Echoes back to client whatever they sent, but capitalized. """

    async def on_websocket(self, route: str, ws: web.WebSocketResponse):
        """Identify the demo server"""
        await ws.send_str("Connected to demo {}".format(self.__class__.__name__))
        await super().on_websocket(route, ws)

    async def on_message(self, route: str, ws: web.WebSocketResponse, ws_msg_from_client: aiohttp.WSMessage):
        # print("Capitalize response loop:", id(asyncio.get_event_loop()))
        if ws_msg_from_client.type == web.WSMsgType.TEXT:
            cap = str(ws_msg_from_client.data).upper()
            await ws.send_str(cap)
        elif ws_msg_from_client.type == web.WSMsgType.CLOSE:
            pass
            # print("Received 'CLOSE' message from websocket")
        else:
            print("Some other message:", ws_msg_from_client)
            # raise Exception(str(ws_msg_from_client))


class RandomQuoteHandler(WebsocketHandler):
    """ Sends a random quote to the client every so many seconds. """
    QUOTES = ["Wherever you go, there you are.",
              "80% of all statistics are made up.",
              "If a tree falls in the woods, and no one is around to hear it, does it make a noise?"]

    def __init__(self, interval: float = 10, count=333, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.interval = interval
        self.count = count

    async def on_websocket(self, route: str, ws: web.WebSocketResponse):
        """
        Override this function if you want to handle new incoming websocket clients.
        The default behavior is to listen indefinitely for incoming messages from clients
        and call on_message() with each one.
        """
        await ws.send_str("Connected to demo {}".format(self.__class__.__name__))
        await ws.send_str("Sending {} quotes with {} second delays".format(self.count, self.interval))

        async def _regular_interval():
            counter = 0
            while not ws.closed and counter < self.count:
                # print("LOOP BEGINNING AGAIN", flush=True)
                await asyncio.sleep(1)
                quote = random.choice(self.QUOTES)
                try:
                    print("Sending quote:", quote)
                    await ws.send_json({"quote": quote})
                    counter += 1

                    if ws.exception():
                        print("ws.exception()")
                        raise ws.exception()

                    if counter >= self.count:
                        await ws.close()
                    else:
                        await asyncio.sleep(self.interval)

                except Exception as ex:
                    print("Exception", ex)
                    traceback.print_tb(sys.exc_info()[2])
                    return

        asyncio.create_task(_regular_interval())
        await super().on_websocket(route, ws)  # Block here until socket dies

        # print("on_websocket last line within RandomQuoteServer", self)


class TimeOfDayHandler(WebsocketHandler):
    """ Sends a message to all clients simultaneously about time of day. """

    def __init__(self, interval: float = 2, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.interval = interval
        self.task = None  # type: asyncio.Task

    async def on_websocket(self, route: str, ws: web.WebSocketResponse):

        # Lazily start up the time ticker, but notice that all connections
        # receive the broadcast simultaneously.
        async def _regular_interval():
            while True:
                if int(time.time()) % self.interval == 0:  # Only on the x second mark
                    timestamp = "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())
                    await self.broadcast_json({"timestamp": timestamp})
                await asyncio.sleep(1)

        if not self.task:
            self.task = asyncio.create_task(_regular_interval())

        return await super().on_websocket(route, ws)


if __name__ == "__main__":
    main()
