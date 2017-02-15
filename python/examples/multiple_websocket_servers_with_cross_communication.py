#!/usr/bin/env python3
"""
Illustrates how to have multiple websocket servers running and send
messages to all their various clients at once.

In response to stackoverflow question:
http://stackoverflow.com/questions/35820782/how-to-manage-websockets-across-multiple-servers-workers

Pastebin: http://pastebin.com/xDSACmdV
"""
import asyncio
import datetime
import random
import time
import webbrowser

import aiohttp
from aiohttp import web

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


def main():
    # Create servers
    cap_srv = CapitalizeEchoServer(port=9990)
    rnd_srv = RandomQuoteServer(port=9991)
    tim_srv = TimeOfDayServer(port=9992)

    # Queue their start operation
    loop = asyncio.get_event_loop()
    loop.create_task(cap_srv.start())
    loop.create_task(rnd_srv.start())
    loop.create_task(tim_srv.start())

    # Open web pages to test them
    webtests = [9990, 9991, 9991, 9992, 9992]
    for port in webtests:
        url = "http://www.websocket.org/echo.html?location=ws://localhost:{}".format(port)
        webbrowser.open(url)
    print("Be sure to click 'Connect' on the webpages that just opened.")

    # Queue a simulated broadcast-to-all message
    def _alert_all(msg):
        print("Sending alert:", msg)
        msg_dict = {"alert": msg}
        cap_srv.broadcast_message(msg_dict)
        rnd_srv.broadcast_message(msg_dict)
        tim_srv.broadcast_message(msg_dict)

    loop.call_later(17, _alert_all, "ALL YOUR BASE ARE BELONG TO US")

    # async def _close_all(delay):
    #     await asyncio.sleep(delay)
    #     await cap_srv.close()
    #     await rnd_srv.close()
    #     await tim_srv.close()
    #
    # loop.create_task(_close_all(30))

    # Run event loop
    loop.run_forever()


class MyServer:
    def __init__(self, port):
        self.port = port  # type: int
        self.loop = None  # type: asyncio.AbstractEventLoop
        self.app = None  # type: web.Application
        self.srv = None  # type: asyncio.base_events.Server

    async def start(self):
        self.loop = asyncio.get_event_loop()
        self.app = web.Application()
        self.app["websockets"] = []  # type: [web.WebSocketResponse]
        self.app.router.add_get("/", self._websocket_handler)
        await self.app.startup()
        handler = self.app.make_handler()
        self.srv = await asyncio.get_event_loop().create_server(handler, port=self.port)
        print("{} listening on port {}".format(self.__class__.__name__, self.port))

    async def close(self):
        assert self.loop is asyncio.get_event_loop()
        self.srv.close()
        await self.srv.wait_closed()

        for ws in self.app["websockets"]:  # type: web.WebSocketResponse
            await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown')

        await self.app.shutdown()
        await self.app.cleanup()

    async def _websocket_handler(self, request):
        assert self.loop is asyncio.get_event_loop()
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.app["websockets"].append(ws)

        await self.do_websocket(ws)

        self.app["websockets"].remove(ws)
        return ws

    async def do_websocket(self, ws: web.WebSocketResponse):
        async for ws_msg in ws:  # type: aiohttp.WSMessage
            pass

    def broadcast_message(self, msg: dict):
        for ws in self.app["websockets"]:  # type: web.WebSocketResponse
            ws.send_json(msg)


class CapitalizeEchoServer(MyServer):
    """ Echoes back to client whatever they sent, but capitalized. """

    async def do_websocket(self, ws: web.WebSocketResponse):
        async for ws_msg in ws:  # type: aiohttp.WSMessage
            cap = ws_msg.data.upper()
            ws.send_str(cap)


class RandomQuoteServer(MyServer):
    """ Sends a random quote to the client every so many seconds. """
    QUOTES = ["Wherever you go, there you are.",
              "80% of all statistics are made up.",
              "If a tree falls in the woods, and no one is around to hear it, does it make a noise?"]

    def __init__(self, interval: float = 10, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.interval = interval

    async def do_websocket(self, ws: web.WebSocketResponse):
        async def _regular_interval():
            while self.srv.sockets is not None:
                quote = random.choice(RandomQuoteServer.QUOTES)
                ws.send_json({"quote": quote})
                await asyncio.sleep(self.interval)

        self.loop.create_task(_regular_interval())

        await super().do_websocket(ws)  # leave client connected here indefinitely


class TimeOfDayServer(MyServer):
    """ Sends a message to all clients simultaneously about time of day. """

    async def start(self):
        await super().start()

        async def _regular_interval():
            while self.srv.sockets is not None:
                if int(time.time()) % 10 == 0:  # Only on the 10 second mark
                    timestamp = "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())
                    self.broadcast_message({"timestamp": timestamp})
                await asyncio.sleep(1)

        self.loop.create_task(_regular_interval())


if __name__ == "__main__":
    main()
