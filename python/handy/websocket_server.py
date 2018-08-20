#!/usr/bin/env python3
"""
Easy to use Websocket Server.

Source: https://github.com/rharder/handy

June 2018 - Updated for aiohttp v3.3
August 2018 - Updated for Python 3.7
"""
import asyncio
import weakref
from functools import partial
from typing import Dict

import aiohttp  # pip install aiohttp
import logging
from aiohttp import web

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


# class WsServerSingleRouteDEPRECATED(object):
#     def __init__(self, port: int = 8000, route: str = "/"):
#         """
#         Create a new WsServer that will listen on the given port and at the given route.
#         The default port is 8000, and the default route is /, ie, by default the server
#         will listen at http://localhost:8000/
#
#         :param port: The port on which to listen
#         :param route: The route at which to listen
#         """
#         super().__init__()
#         self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)
#
#         # Passed parameters
#         self.port = port
#         self.route = route
#
#         # Internal use
#         # self.websockets = []  # type: [web.WebSocketResponse]
#         # self.loop = None  # type: asyncio.AbstractEventLoop
#         self.app = None  # type: web.Application
#         self.site = None  # type: web.TCPSite
#         self.runner = None  # type: web.AppRunner
#         self._running = False  # type: bool
#         self._shutting_down = False  # type: bool
#
#     def __str__(self):
#         return "{}({}:{})".format(self.__class__.__name__, self.port, self.route)
#
#     @property
#     def running(self):
#         # print("running = false but really", self._running)
#         # return False
#         return self._running
#
#     @property
#     def shutting_down(self):
#         return self._shutting_down
#
#     async def close(self):
#         if not self._shutting_down:
#             self._shutting_down = True
#             # await self.runner.cleanup()
#             asyncio.create_task(self.runner.cleanup())
#         else:
#             print("Already shutting down, says self.close()", flush=True)
#             # raise Exception("Already shutting down")
#
#     async def _on_shutdown(self, app):
#         print("_on_shutdown", app, flush=True)
#         await self.close_websockets()
#         self._running = False
#
#         print("Exiting system...")
#         loop = asyncio.get_event_loop()
#         # loop.stop()
#         # asyncio.create_task(asyncio.sleep(1))
#
#     async def close_websockets(self):
#         print("close_websockets called", flush=True)
#         for ws in set(self.app['websockets']):  # type: web.WebSocketResponse
#             print("Closing websocket", ws, flush=True)
#             await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown')
#             # await asyncio.sleep(0)
#             # ws.cancel()
#             print("Closed", ws, flush=True)
#
#     async def start(self, port: int = None, route: str = None):
#         """
#         Starts the websocket server and begins listening on a given port and at
#         a given route.  These values can be provided in the __init__() constructor
#         or at the time start() is called.  The parameters given in start() will
#         override whatever was provided in the constructor.
#
#         :param port: The port on which to listen (overrides the constructor values)
#         :param route: The route at which to lsiten (overrides the constructor values)
#         :return: None
#         """
#         self.route = route or self.route
#         self.port = port or self.port
#
#         self.app = web.Application()
#         self.app['websockets'] = weakref.WeakSet()
#         self.app.router.add_get(self.route, self.websocket_handler)
#         # self.app.router.add_get(self.route, lambda x: self.websocket_handler(route, x))
#         self.app.on_shutdown.append(self._on_shutdown)
#
#         self.runner = web.AppRunner(self.app)
#         await self.runner.setup()
#         self.site = web.TCPSite(self.runner, 'localhost', port=self.port)
#         await self.site.start()
#         self._running = True
#
#     async def websocket_handler(self, request: web.BaseRequest):
#         """
#         Handles the incoming websocket client connection and calls on_websocket()
#         in order to hand off control to subclasses of the server.
#
#         If this server is being attached to an existing web.Application(), this function
#         may be added as a route to that app without using this class's start() and close() functions,
#         although you can still use the close_websockets() function (and should) when closing
#         your web.Application().
#         """
#         ws = web.WebSocketResponse()
#         await ws.prepare(request)
#         await ws.send_str("Connected: {}".format(str(ws)))
#
#         # self.websockets.append(ws)
#         self.app['websockets'].add(ws)
#         try:
#             await self.on_websocket(ws)
#         finally:
#             self.app['websockets'].discard(ws)
#         print("Departing websocket_handler in WsServer")
#         return ws
#
#     async def on_websocket(self, ws: web.WebSocketResponse):
#         """
#         Override this function if you want to handle new incoming websocket clients.
#         The default behavior is to listen indefinitely for incoming messages from clients
#         and call on_message() with each one.
#         """
#         while self.running and not self.shutting_down:
#             # print("RE-ENTERING on_websocket while loop")
#             try:
#                 ws_msg = await ws.receive()  # type: aiohttp.WSMessage
#             except RuntimeError as e:  # Socket closing throws RuntimeError
#                 # print("RuntimeError - did socket close?", e, flush=True)
#                 break
#             else:
#                 # Call on_message() if it got something
#                 try:
#                     await self.on_message(ws=ws, ws_msg_from_client=ws_msg)
#                 except RuntimeError as e:
#                     # Probably the socket is closing
#                     # print("await on_message aborted", flush=True)
#                     break
#
#         # print("on_websocket last line within WsServer", self)
#
#     async def on_message(self, ws: web.WebSocketResponse, ws_msg_from_client: aiohttp.WSMessage):
#         """ Override this function to handle incoming messages from websocket clients. """
#         pass
#
#     async def broadcast_json(self, msg):
#         """ Converts msg to json and broadcasts the json data to all connected clients. """
#         if self.running:
#             for ws in set(self.app['websockets']):  # type: web.WebSocketResponse
#                 await ws.send_json(msg)
#
#     async def broadcast_text(self, msg: str):
#         """ Broadcasts a string to all connected clients. """
#         if self.running:
#             for ws in set(self.app['websockets']):  # type: web.WebSocketResponse
#                 await ws.send_str(msg)
#
#     async def broadcast_bytes(self, msg: bytes):
#         """ Broadcasts bytes to all connected clients. """
#         if self.running:
#             for ws in set(self.app['websockets']):  # type: web.WebSocketResponse
#                 await ws.send_bytes(msg)


class WsServerMultiRoutes(object):
    """Hosts a websocket server on a given port and responds to multiple routes
    (relative urls) at that address.

    This is the preferred server over the WsServerSingleRoute option.
    """

    def __init__(self, port):
        """
        Create a new WsServer that will listen on the given port.
        The default port is 8000.

        :param port: The port on which to listen
        """
        super().__init__()
        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        # Passed parameters
        self.port = port

        # Internal use
        self.app = None  # type: web.Application
        self.site = None  # type: web.TCPSite
        self.runner = None  # type: web.AppRunner
        self.route_handlers = {}  # type: Dict[str, WsHandler]

        self._running = False  # type: bool
        self._shutting_down = False  # type: bool
        self._starting_up = False  # type: bool

    def __str__(self):
        routes = ", ".join(self.route_handlers.keys())
        return "{}({}:({})".format(self.__class__.__name__, self.port, routes)

    @property
    def running(self):
        return self._running

    @property
    def starting_up(self):
        return self._starting_up

    @property
    def shutting_down(self):
        return self._shutting_down

    async def start(self):
        """
        Starts the websocket server and begins listening.  This function returns
        with the server continuing to listen (non-blocking).

        :return: None
        """
        if self.starting_up or self.running:
            raise Exception("Cannot start server when it is already running.")

        self._starting_up = True

        self.app = web.Application()
        self.app['websockets'] = weakref.WeakSet()  # type: web.WebSocketResponse
        self.app['route_to_websockets'] = {}  # type: Dict[str, weakref.WeakSet]
        self.app.on_shutdown.append(self._on_shutdown)

        # Connect routes
        for route in self.route_handlers.keys():
            self.app['route_to_websockets'][route] = weakref.WeakSet()
            self.app.router.add_get(route, partial(self.websocket_handler, route))

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, 'localhost', port=self.port)
        await self.site.start()

        self._running = True
        self._starting_up = False

    async def close(self):
        # print(self.__class__.__name__, "close()", flush=True)
        if not self.running:
            raise Exception("Cannot close server that is not running.")

        if self.shutting_down:
            # print("Already shutting down, says self.close()", flush=True)
            pass
        else:
            self._shutting_down = True
            await self.runner.cleanup()

    async def _on_shutdown(self, app):
        # print(self.__class__.__name__, "_on_shutdown()", flush=True)
        await self.close_websockets()
        self._running = False
        self._shutting_down = False
        # print("_on_shutdown exiting")

    async def close_websockets(self):
        # print(self.__class__.__name__, "close_websockets()", flush=True)

        # for ws in set(self.app['websockets']):
        #     await ws.close()
        #     await asyncio.sleep(0)

        # Technique from
        # https://docs.aiohttp.org/en/stable/faq.html#how-do-i-programmatically-close-a-websocket-server-side
        ws_closers = [ws.close()
                      for ws in set(self.app['websockets'])
                      if not ws.closed]
        ws_closers and await asyncio.gather(*ws_closers)

        # print("close_websockets exiting")

    def add_route(self, route, handler):
        """

        :param str route:
        :param WsHandler handler:
        :return:
        """
        if self.running:
            raise Exception("Cannot add a route after server is already running.")
        self.route_handlers[route] = handler

    async def websocket_handler(self, route: str, request: web.BaseRequest):
        """
        Handles the incoming websocket client connection and calls on_websocket()
        in order to hand off control to subclasses of the server.

        If this server is being attached to an existing web.Application(), this function
        may be added as a route to that app without using this class's start() and close() functions,
        although you can still use the close_websockets() function (and should) when closing
        your web.Application().
        """
        print(self.__class__.__name__, "entering websocket_handler()", flush=True)

        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_str("Connected from route {}: {}".format(route, str(ws)))

        self.app['websockets'].add(ws)
        self.app['route_to_websockets'][route].add(ws)
        try:
            await self.route_handlers[route].on_websocket(ws)
        finally:
            self.app['websockets'].discard(ws)
            self.app['route_to_websockets'][route].discard(ws)
        print("Departing websocket_handler in WsServer")
        return ws

    async def broadcast_json(self, msg, route: str = None):
        """ Converts msg to json and broadcasts the json data to all connected clients. """
        await self._broadcast(msg, route, web.WebSocketResponse.send_json)

    async def broadcast_text(self, msg: str, route: str = None):
        """ Broadcasts a string to all connected clients. """
        await self._broadcast(msg, route, web.WebSocketResponse.send_str)

    async def broadcast_bytes(self, msg: bytes, route: str = None):
        """ Broadcasts bytes to all connected clients. """
        await self._broadcast(msg, route, web.WebSocketResponse.send_bytes)

    async def _broadcast(self, msg, route: str, func: callable):

        sockets = None  # type: set
        if route is None:  # Broadcast to websockets on all routes
            sockets = set(self.app['websockets'])
        else:  # Broadcast only to selected routes
            sockets = set(self.app['route_to_websockets'][route])

        for ws in sockets:  # type: web.WebSocketResponse
            await func(ws, msg)


class WsHandler(object):

    async def on_websocket(self, ws: web.WebSocketResponse):
        """
        Override this function if you want to handle new incoming websocket clients.
        The default behavior is to listen indefinitely for incoming messages from clients
        and call on_message() with each one.

        If you override on_websocket and have your own loop to reseive and process messages,
        you may also need an await asyncio.sleep(0) line to avoid an infinite loop with the
        websocket close message.

        Example:
            while not ws.closed:
                ws_msg = await ws.receive()
                await asyncio.sleep(0)
                ...

        """
        # while self.parent.running and not self.parent.shutting_down:
        # print(self.__class__.__name__, "entering on_websocket()", flush=True)
        try:
            while not ws.closed:
                # print(self.__class__.__name__, "while not ws.closed loop", flush=True)
                ws_msg = await ws.receive()  # type: aiohttp.WSMessage
                await self.on_message(ws=ws, ws_msg_from_client=ws_msg)

                # If you override on_websocket and have your own loop
                # to reseive and process messages, you may also need
                # this await asyncio.sleep(0) line to avoid an infinite
                # loop with the websocket close message.
                await asyncio.sleep(0)  # Need to yield control back to event loop

        except RuntimeError as e:  # Socket closing throws RuntimeError
            print("RuntimeError - did socket close?", e, flush=True)
            # break
            pass

        # print("on_websocket last line within WsServer", self)

    async def on_message(self, ws: web.WebSocketResponse, ws_msg_from_client: aiohttp.WSMessage):
        """ Override this function to handle incoming messages from websocket clients. """
        pass
