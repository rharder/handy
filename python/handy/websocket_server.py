#!/usr/bin/env python3
"""
Easily subclassed websocket server.

For example usage, see examples folder (also here: http://pastebin.com/xDSACmdV)
"""
import asyncio

import aiohttp
import logging
from aiohttp import web

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


class WsServer(object):
    def __init__(self, port: int = 8000, route: str = "/"):
        """
        Create a new WsServer that will listen on the given port and at the given route.
        The default port is 8000, and the default route is /, ie, by default the server
        will listen at http://localhost:8000/

        :param port: The port on which to listen
        :param route: The route at which to listen
        """
        super().__init__()
        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        # Passed parameters
        self.port = port
        self.route = route

        # Internal use
        self.websockets = []  # type: [web.WebSocketResponse]
        self.loop = None  # type: asyncio.AbstractEventLoop
        self.app = None  # type: web.Application
        self.srv = None  # type: asyncio.base_events.Server

    def __str__(self):
        return "{}({}:{})".format(self.__class__.__name__, self.port, self.route)

    async def start(self, port: int = None, route: str = None):
        """
        Starts the websocket server and begins listening on a given port and at
        a given route.  These values can be provided in the __init__() constructor
        or at the time start() is called.  The parameters given in start() will
        override whatever was provided in the constructor.

        :param port: The port on which to listen (overrides the constructor values)
        :param route: The route at which to lsiten (overrides the constructor values)
        :return: None
        """
        self.route = route or self.route
        self.port = port or self.port
        self.loop = asyncio.get_event_loop()

        self.app = web.Application()
        self.app.router.add_get(self.route, self.websocket_handler)
        await self.app.startup()

        handler = self.app.make_handler()
        self.srv = await asyncio.get_event_loop().create_server(handler, port=self.port)

        start_msg = "{} listening on port {}".format(self.__class__.__name__, self.port)
        self.log.info(start_msg)
        print(start_msg)

    async def close(self):
        """ Closes all connections to websocket clients and then shuts down the server. """
        self.srv.close()
        await self.srv.wait_closed()
        await self.close_websockets()
        await self.app.shutdown()
        await self.app.cleanup()

    async def close_websockets(self):
        for ws in self.websockets.copy():  # type: web.WebSocketResponse
            await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown')

    async def websocket_handler(self, request: aiohttp.Request):
        """
        Handles the incoming websocket client connection and calls on_websocket()
        in order to hand off control to subclasses of the server.

        If this server is being attached to an existing web.Application(), this function
        may be added as a route to that app without using this class's start and close functions.
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.websockets.append(ws)
        try:
            await self.on_websocket(ws)
        finally:
            if ws in self.websockets:
                self.websockets.remove(ws)

        return ws

    async def on_websocket(self, ws: web.WebSocketResponse):
        """
        Override this function if you want to handle new incoming websocket clients.
        The default behavior is to listen indefinitely for incoming messages from clients
        and call on_message() with each one.
        """
        async for ws_msg in ws:  # type: aiohttp.WSMessage
            await self.on_message(ws=ws, ws_msg_from_client=ws_msg)

    async def on_message(self, ws: web.WebSocketResponse, ws_msg_from_client: aiohttp.WSMessage):
        """ Override this function to handle incoming messages from websocket clients. """
        pass

    def broadcast_json(self, msg):
        """ Converts msg to json and broadcasts the json data to all connected clients. """
        for ws in self.websockets.copy():  # type: web.WebSocketResponse
            ws.send_json(msg)

    def broadcast_text(self, msg: str):
        """ Broadcasts a string to all connected clients. """
        for ws in self.websockets.copy():  # type: web.WebSocketResponse
            ws.send_str(msg)

    def broadcast_bytes(self, msg: bytes):
        """ Broadcasts bytes to all connected clients. """
        for ws in self.websockets.copy():  # type: web.WebSocketResponse
            ws.send_bytes(msg)
