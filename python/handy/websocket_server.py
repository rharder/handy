#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Easy to use Websocket Server.

Source: https://github.com/rharder/handy

June 2018 - Updated for aiohttp v3.3
August 2018 - Updated for Python 3.7, made WebServer support multiple routes on one port
"""
import asyncio
import inspect
import logging
import weakref
from functools import partial
from typing import Dict, Set, List, Optional, Coroutine, Any, Callable, Tuple, Awaitable, Union

import aiohttp  # pip install aiohttp
from aiohttp import web, hdrs

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"
__homepage__ = "https://github.com/rharder/handy"

from aiohttp.typedefs import Handler

logger = logging.getLogger(__name__)


class WebServer:
    """Hosts a web/websocket server on a given port and responds to multiple routes
    (relative urls) at that address.


    Source: https://github.com/rharder/handy
    Author: Robert Harder
    License: Public Domain

    """

    def __init__(self, host: str = None, port: int = None, ssl_context=None):
        """
        Create a new WebServer that will listen on the given port.

        :param port: The port on which to listen
        """
        super().__init__()

        # Passed parameters
        self.host: str = host
        self.port: int = port
        self.ssl_context = ssl_context

        # Internal use
        self.app: web.Application = web.Application()
        self.site: Optional[web.TCPSite] = None
        self.runner: Optional[web.AppRunner] = None
        self.route_handlers: Dict[str, Callable[[str, web.BaseRequest], web.Response]] = {}
        self.ws_route_handlers: Dict[str, WebsocketHandler] = {}
        self.static_handlers: Dict[str, Dict] = {}

        self._all_handlers: Dict[str, Tuple[str, Union[Handler, WebHandler]]] = dict()

        self._running: bool = False
        self._shutting_down: bool = False
        self._starting_up: bool = False

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

        self.app['requests'] = []  # type: List[web.BaseRequest]
        self.app.on_shutdown.append(self._on_shutdown)

        # All Route Types
        # for _method, _path, _handler in self._all_handlers:
        for _route, _val in self._all_handlers.items():
            _method, _handler = _val
            self.app.router.add_route(method=_method, path=_route, handler=partial(self.incoming_http_handler, _route))

        # # Connect routes
        # for _route in self.route_handlers.keys():  # Dynamic handlers
        #     # noinspection PyTypeChecker
        #     self.app.router.add_get(_route, partial(self.incoming_http_handler, _route))
        #
        # for _ws_route, _ws_handler in self.ws_route_handlers.items():
        #     # noinspection PyTypeChecker
        #     self.app.router.add_get(_ws_route, handler=_ws_handler)

        for _url_path, _kwargs in self.static_handlers.items():  # Static directory handlers
            self.app.router.add_static(_url_path, **_kwargs)

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, port=self.port, host=self.host, ssl_context=self.ssl_context)
        await self.site.start()

        self._running = True
        self._starting_up = False

    async def shutdown(self):
        if not self.running:
            raise Exception("Cannot close server that is not running.")

        if self.shutting_down:
            pass
        else:
            self._shutting_down = True
            await self.runner.cleanup()

    async def _on_shutdown(self, _: web.Application):
        self.close_current_connections()
        self._running = False
        self._shutting_down = False

    def close_current_connections(self):
        for x in self.app["requests"]:
            if x is not None and x.transport is not None:
                x.transport.close()

    def add_get_route(self, route, handler):
        return self.add_route(hdrs.METH_GET, route, handler)

    def add_post_route(self, route, handler):
        return self.add_route(hdrs.METH_POST, route, handler)

    def add_route(self, method: str, route: str, handler):
        if self.running:
            raise RuntimeError("Cannot add a route after server is already running.")
        # self._all_handlers.append((method, route, handler))
        self._all_handlers[route] = (method, handler)

    # def add_route(self, route: str, handler):
    #     if self.running:
    #         raise RuntimeError("Cannot add a route after server is already running.")
    #     self.route_handlers[route] = handler

    # def add_websocket_route(self, route: str, ws_handler):
    #     if self.running:
    #         raise RuntimeError("Cannot add a route after server is already running.")
    #     self.ws_route_handlers[route] = ws_handler

    def add_static(self, url_path: str, local_path: str, **kwargs):
        """
        Add a static route from the given url_path to the given local_path.

        Example:
        srv.add_static("/www", "./htdocs")
        :param url_path: path in the url
        :param local_path: path to local directory
        :param kwargs: other args from aiohttp.web_routedef.UrlDispatcher.add_static()
        :return:
        """
        # server.app.router.add_static("/www", self.htdocs, show_index=False)
        if self.running:
            raise RuntimeError("Cannot add a static route after server is already running.")
        kwargs = kwargs or {}
        kwargs["path"] = local_path
        self.static_handlers[url_path] = kwargs

    async def incoming_http_handler(self, route: str, request: web.BaseRequest) -> web.Response:
        self.app['requests'].append(request)
        resp = None
        try:
            if route in self._all_handlers:
                _method, _handler = self._all_handlers[route]
                if isinstance(_handler, WebHandler):
                    logger.info(f"Calling WebHandler for {route}: {_handler}")
                    resp = await _handler.on_incoming_http(route=route, request=request)
                elif asyncio.iscoroutinefunction(_handler):
                    logger.info(f"Awaiting coroutine for {route}: {_handler}")
                    resp = await _handler(route, request)
                elif callable(_handler):
                    logger.info(f"Calling function for {route}: {_handler}")
                    resp = _handler(route, request)
        finally:
            self.app['requests'].remove(request)
        return resp


class WebHandler:

    async def on_incoming_http(self, route: str, request: web.BaseRequest) -> web.Response:
        return web.Response(body=str(self.__class__.__name__))


class WebsocketHandler(WebHandler):

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.websockets: Set[web.WebSocketResponse] = weakref.WeakSet()

    async def broadcast_json(self, msg):
        """ Converts msg to json and broadcasts the json data to all connected clients. """
        await self._broadcast(msg, web.WebSocketResponse.send_json)

    async def broadcast_text(self, msg: str):
        """ Broadcasts a string to all connected clients. """
        await self._broadcast(msg, web.WebSocketResponse.send_str)

    async def broadcast_bytes(self, msg: bytes):
        """ Broadcasts bytes to all connected clients. """
        await self._broadcast(msg, web.WebSocketResponse.send_bytes)

    async def _broadcast(self, msg, func: callable):
        for ws in set(self.websockets):  # type: web.WebSocketResponse
            await func(ws, msg)

    async def close_websockets(self):
        """Closes all active websockets for this handler."""
        ws_closers = [ws.close() for ws in set(self.websockets) if not ws.closed]
        ws_closers and await asyncio.gather(*ws_closers)

    async def on_incoming_http(self, route: str, request: web.BaseRequest):
        """Handles the incoming http(s) request and converts it to a WebSocketResponse.

        This method is not meant to be overridden when subclassed.
        """
        ws = web.WebSocketResponse()
        self.websockets.add(ws)
        try:
            await ws.prepare(request)
            await self.on_websocket(route, ws)
        finally:
            self.websockets.discard(ws)
            return ws

    async def on_websocket(self, route: str, ws: web.WebSocketResponse):
        """
        Override this function if you want to handle new incoming websocket clients.
        The default behavior is to listen indefinitely for incoming messages from clients
        and call on_message() with each one.

        If you override on_websocket and have your own loop to receive and process messages,
        you may also need an await asyncio.sleep(0) line to avoid an infinite loop with the
        websocket close message.

        Example:
            while not ws.closed:
                ws_msg = await ws.receive()
                await asyncio.sleep(0)
                ...

        """
        try:
            while not ws.closed:
                ws_msg = await ws.receive()  # type: aiohttp.WSMessage
                await self.on_message(route=route, ws=ws, ws_msg_from_client=ws_msg)

                # If you override on_websocket and have your own loop
                # to receive and process messages, you may also need
                # this await asyncio.sleep(0) line to avoid an infinite
                # loop with the websocket close message.
                await asyncio.sleep(0)  # Need to yield control back to event loop

        except RuntimeError as e:  # Socket closing throws RuntimeError
            print("RuntimeError - did socket close?", e, flush=True)
            pass
        finally:
            await self.on_close(route, ws)

    async def on_message(self, route: str, ws: web.WebSocketResponse, ws_msg_from_client: aiohttp.WSMessage):
        """ Override this function to handle incoming messages from websocket clients. """
        pass

    async def on_close(self, route: str, ws: web.WebSocketResponse):
        """ Override this function to handle a websocket having closed. """
        pass
