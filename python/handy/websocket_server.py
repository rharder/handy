#!/usr/bin/env python3
"""
Easily subclassed websocket server.

For example usage, see examples folder (also here: http://pastebin.com/xDSACmdV)
Source: https://github.com/rharder/handy

June 2018 - Updated for aiohttp v3.3
"""
import asyncio
import weakref

import aiohttp  # pip install aiohttp  # Tested up to aiohttp==2.1.0
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
        # self.websockets = []  # type: [web.WebSocketResponse]
        # self.loop = None  # type: asyncio.AbstractEventLoop
        self.app = None  # type: web.Application
        self.site = None  # type: web.TCPSite
        self.runner = None  # type: web.AppRunner
        self._running = False  # type: bool
        self._shutting_down = False  # type: bool
        # self.srv = None  # type: asyncio.base_events.Server

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

        self.app = web.Application()
        self.app.on_shutdown.append(self._on_shutdown)
        self.app['websockets'] = weakref.WeakSet()
        self.app.router.add_get(self.route, self.websocket_handler)

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, 'localhost', self.port)
        await self.site.start()
        self._running = True

        start_msg = "{} listening on port {}".format(self.__class__.__name__, self.port)
        self.log.info(start_msg)
        print(start_msg)

    async def close(self):
        """ Closes all connections to websocket clients and then shuts down the server. """

        if not self._shutting_down:
            self._shutting_down = True
            # await self.runner.cleanup()
            asyncio.create_task(self.runner.cleanup())
        #
        # print("close called", self.__class__.__name__)
        #
        # print("self.runner.cleanup() queuing...")
        # # cleanup will in turn cause _on_shutdown to be run
        # # await self.runner.cleanup()
        # asyncio.create_task(self.runner.cleanup())
        # print("self.runner.cleanup queued")

    async def _on_shutdown(self, app):
        """Callback for when self.runner gets cleaned up."""
        print("_on_shutdown", self.__class__.__name__, app, flush=True)
        await self.close_websockets()
        self._running = False
        print("end of _on_shutdown", flush=True)
        # for ws in set(app['websockets']):
        #     print("Closing socket", ws, flush=True)
        #     await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown')
        #     print("Closed", ws)
        # print("runner cleanup...")
        # await self.runner.cleanup()
        # print("runner cleaned.")
        # print("Exiting system...")

        # loop = asyncio.get_event_loop()
        # loop.run_until_complete(asyncio.sleep(2))
        # loop.stop()

        # print("_on_shutdown called)")
        # await self.close_websockets()
        # # asyncio.get_event_loop().stop()

    @property
    def running(self):
        return self._running

    async def close_websockets(self):
        print("close_websockets called")
        for ws in set(self.app['websockets']):  # type: web.WebSocketResponse
            print("Closing websocket", ws)
            await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown')
            print("Closed", ws)
        print("end of close_websockets", flush=True)

    async def websocket_handler(self, request: web.BaseRequest):
        """
        Handles the incoming websocket client connection and calls on_websocket()
        in order to hand off control to subclasses of the server.

        If this server is being attached to an existing web.Application(), this function
        may be added as a route to that app without using this class's start() and close() functions,
        although you can still use the close_websockets() function (and should) when closing
        your web.Application().
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # self.websockets.append(ws)
        self.app['websockets'].add(ws)
        try:
            await self.on_websocket(ws)
        finally:
            # if ws in self.websockets:
            #     self.websockets.remove(ws)
            self.app['websockets'].discard(ws)
        return ws

    async def on_websocket(self, ws: web.WebSocketResponse):
        """
        Override this function if you want to handle new incoming websocket clients.
        The default behavior is to listen indefinitely for incoming messages from clients
        and call on_message() with each one.
        """
        while True:
            try:
                ws_msg = await ws.receive()  # type: aiohttp.WSMessage
            except RuntimeError as e:  # Socket closing throws RuntimeError
                # print("RuntimeError - did socket close?", e, flush=True)
                break
            else:
                # Call on_message() if it got something
                try:
                    await self.on_message(ws=ws, ws_msg_from_client=ws_msg)
                except RuntimeError as e:
                    # Probably the socket is closing
                    # Exception seen during development:
                    #   This event loop is already running
                    # print("await on_message aborted")
                    break

        print("on_websocket last line", self)

    async def on_message(self, ws: web.WebSocketResponse, ws_msg_from_client: aiohttp.WSMessage):
        """ Override this function to handle incoming messages from websocket clients. """
        pass

    async def broadcast_json(self, msg):
        """ Converts msg to json and broadcasts the json data to all connected clients. """

        if self.running:
            for ws in set(self.app['websockets']):  # type: web.WebSocketResponse
                await ws.send_json(msg)

    async def broadcast_text(self, msg: str):
        """ Broadcasts a string to all connected clients. """

        if self.running:
            for ws in set(self.app['websockets']):  # type: web.WebSocketResponse
                await ws.send_str(msg)

    async def broadcast_bytes(self, msg: bytes):
        """ Broadcasts bytes to all connected clients. """

        if self.running:
            for ws in set(self.app['websockets']):  # type: web.WebSocketResponse
                await ws.send_bytes(msg)
