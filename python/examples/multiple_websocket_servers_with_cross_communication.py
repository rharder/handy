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

from handy.websocket_server import WsServer

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


def main():
    # Create servers
    cap_srv = CapitalizeEchoServer(port=9990)
    rnd_srv = RandomQuoteServer(port=9991, interval=10)
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
        cap_srv.broadcast_json(msg_dict)
        rnd_srv.broadcast_json(msg_dict)
        tim_srv.broadcast_json(msg_dict)

    loop.call_later(17, _alert_all, "ALL YOUR BASE ARE BELONG TO US")

    # Run event loop
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(cap_srv.close())
        loop.run_until_complete(rnd_srv.close())
        loop.run_until_complete(tim_srv.close())
        loop.close()


class CapitalizeEchoServer(WsServer):
    """ Echoes back to client whatever they sent, but capitalized. """

    async def on_message(self, ws: web.WebSocketResponse, ws_msg_from_client: aiohttp.WSMessage):
        cap = ws_msg_from_client.data.upper()
        ws.send_str(cap)


class RandomQuoteServer(WsServer):
    """ Sends a random quote to the client every so many seconds. """
    QUOTES = ["Wherever you go, there you are.",
              "80% of all statistics are made up.",
              "If a tree falls in the woods, and no one is around to hear it, does it make a noise?"]

    def __init__(self, interval: float = 10, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.interval = interval

    async def on_websocket(self, ws: web.WebSocketResponse):

        async def _regular_interval():
            while self.srv.sockets is not None:
                quote = random.choice(RandomQuoteServer.QUOTES)
                print("Sending", quote, flush=True)
                ws.send_json({"quote": quote})
                await asyncio.sleep(self.interval)

        loop = asyncio.get_event_loop()
        task = loop.create_task(_regular_interval())
        try:
            await super().on_websocket(ws)  # leave client connected here indefinitely
        finally:
            task.cancel()


class TimeOfDayServer(WsServer):
    """ Sends a message to all clients simultaneously about time of day. """

    async def start(self, *kargs, **kwargs):
        await super().start(*kargs, **kwargs)

        async def _regular_interval():
            while self.srv.sockets is not None:
                if int(time.time()) % 10 == 0:  # Only on the 10 second mark
                    timestamp = "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())
                    self.broadcast_json({"timestamp": timestamp})
                await asyncio.sleep(1)

        loop = asyncio.get_event_loop()
        self.task = loop.create_task(_regular_interval())

    async def close(self):
        self.task.cancel()
        await super().close()


if __name__ == "__main__":
    main()
