#!/usr/bin/env python3
"""
Easily subclassed websocket server.

For example usage, see examples folder (also here: http://pastebin.com/xDSACmdV)
"""
import asyncio

import aiohttp
from aiohttp import web

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


class WsServer:
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
