import asyncio
import threading

import aiohttp
from aiohttp import web
from yarl import URL

from .connector import Connector, ConnectorListener


class WsServerConnector(Connector):
    def __init__(self, host="127.0.0.1", port=8080, ssl_context=None):
        super().__init__()

        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.url = None

        self.app = web.Application()
        self.app.router.add_get("/", self.websocket_handler)
        self.active_sockets = []  # type: [web.WebSocketResponse]

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.url)

    def connect(self, listener: ConnectorListener, loop=None) -> Connector:
        super().connect(listener, loop)

        self.loop.run_until_complete(self.app.startup())
        self.handler = self.app.make_handler()
        self.srv = self.loop.run_until_complete(self.loop.create_server(self.handler, host=self.host,
                                                                        port=self.port, ssl=self.ssl_context))

        scheme = 'https' if self.ssl_context else 'http'
        url = URL('{}://localhost'.format(scheme))
        self.url = url.with_host(self.host).with_port(self.port)
        self.log.info("Websocket server listening at {}".format(self.url))

        self.listener.connection_made(self)  # Must notify NetworkMemory
        return self

    def send_message(self, msg: dict):
        self.log.debug("Sending update to {} connected clients".format(len(self.active_sockets)))
        for ws in self.active_sockets.copy():
            ws.send_json(msg)

    def close(self):
        self.log.info("Closing websocket server that was listening at {}".format(self.url))
        self.srv.close()
        self.loop.run_until_complete(self.srv.wait_closed())
        self.loop.run_until_complete(self.app.shutdown())
        self.loop.run_until_complete(self.handler.shutdown(shutdown_timeout=10))
        self.loop.run_until_complete(self.app.cleanup())

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.active_sockets.append(ws)
        self.log.info("Client connected to websocket server {}: {}".format(self.url, ws))

        async for msg in ws:  # type: aiohttp.WSMessage
            if msg.type == aiohttp.WSMsgType.TEXT:
                self.listener.message_received(self, msg.json())

            elif msg.type == aiohttp.WSMsgType.ERROR:
                self.log.error("Websocket connection error: {}".format(ws.exception()))
                self.listener.connection_error(self, ws.exception())

        self.log.info("Client disconnected to websocket server {}: {}".format(self.url, ws))
        self.active_sockets.remove(ws)
        return ws


class WsClientConnector(Connector):
    def __init__(self, url: str = None, loop: asyncio.BaseEventLoop = None):
        super().__init__()
        self.url = url
        self.loop = loop or asyncio.get_event_loop()
        self.session = None  # type: aiohttp.ClientSession
        self.ws = None  # type: aiohttp.ClientWebSocketResponse

    def connect(self, listener: ConnectorListener, loop: asyncio.BaseEventLoop = None) -> Connector:
        super().connect(listener, loop)

        async def _connect():
            self.session = aiohttp.ClientSession()
            async with self.session.ws_connect(self.url) as ws:  # type: aiohttp.ClientWebSocketResponse
                self.ws = ws
                self.log.info("Websocket client connected: {}".format(ws))
                self.listener.connection_made(self)  # Must register with NetworkMemory

                async for msg in ws:  # type: aiohttp.WSMessage
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        self.listener.message_received(self, msg.json())

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        self.log.error("Websocket connection error: {}".format(ws.exception()))
                        self.listener.connection_error(self, ws.exception())

        self.loop.create_task(_connect())
        return self

    def send_message(self, msg: dict):
        self.log.debug("Sending message to websocket server {}".format(self.ws))
        self.ws.send_json(msg)

    def close(self):
        self.loop.run_until_complete(self.ws.close())
