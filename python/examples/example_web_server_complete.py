#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper asyncio queue.
"""
import argparse
import asyncio
import logging
from pathlib import Path

from typing import Optional, NoReturn, Dict

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"

import aiohttp
from aiohttp import web

from handy import log_config
from handy.websocket_server import WebServer, WebsocketHandler

logger = logging.getLogger(__name__)


def main():
    args = parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO

    log_config.config(
        console_level=log_level,
        console_formatter=log_config.LogFormat.color_formatter,
        hush=["websockets", "asyncio", "aiohttp.access"]
    )

    app = WebServerExampleApp(port=args.port)
    asyncio.get_event_loop().run_until_complete(app.run())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("--port", type=int, metavar="NUM",
                        help=f"Port for serving http endpoint (default {WebServerExampleApp.DEFAULT_PORT})",
                        default=WebServerExampleApp.DEFAULT_PORT)
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()
    return args


class WebServerExampleApp():
    DEFAULT_PORT: int = 8080

    def __init__(self, port: int = None, verbose: bool = None):
        self.port: int = port or self.DEFAULT_PORT
        self.verbose: bool = bool(verbose)
        self.server: Optional[WebServer] = None
        self.web_handler: Optional[WebsocketHandler] = None
        self.close_requested: bool = False

    async def run(self):
        logger.info("Starting app...")
        self.web_handler = ExampleWebHandler()
        self.server = WebServer(host="0.0.0.0", port=self.port)
        self.server.add_get_route("/", self.web_handler.handle_redirect)
        self.server.add_static("/static", Path(__file__).parent.joinpath("example_html"))
        self.server.add_get_route("/stats", self.web_handler.handle_stats_route)
        self.server.add_get_route("/ws", self.web_handler)  # Websocket!
        self.server.add_post_route("/savethings", self.web_handler.handle_save_things_route)

        logger.info(
            f"Starting webserver on port={self.port}, "
            f"http://localhost:{self.port}")
        await self.server.start()

        while self.server.running:
            if not self.close_requested:
                await asyncio.sleep(10)


class ExampleWebHandler(WebsocketHandler):

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.count_websocket_messages: int = 0
        self.count_incoming_requests: int = 0
        self.count_post_requests: int = 0

    async def handle_redirect(self, route: str, request: web.BaseRequest) -> NoReturn:
        self.count_incoming_requests += 1
        raise web.HTTPFound("/static/index.html")

    async def handle_stats_route(self, route: str, request: web.BaseRequest) -> web.Response:
        self.count_incoming_requests += 1
        return web.json_response({
            "countWebsocketMessages": self.count_websocket_messages,
            "countIncomingRequests": self.count_incoming_requests,
            "countPostRequests": self.count_post_requests,
            "somethingSpecial": "happens here",
            "moreData": [1, 2, 3, 4],
            "whatever": "you need",
        })

    async def handle_save_things_route(self, route: str, request: web.BaseRequest) -> web.Response:
        self.count_incoming_requests += 1
        self.count_post_requests += 1
        data = await request.post()
        print(data)
        username = data.get("username")

        file_info = data.get("file")
        if file_info:
            file_content = file_info.file.read()
            file_name = file_info.filename
            file_record = {
                "name": file_name,
                "size": len(file_content),
            }
        else:
            file_record = {
                "error": "No file was uploaded"
            }

        return web.json_response(
            {"youSentUs": {
                "username": username,
                "file": file_record
            }})

    async def on_websocket(self, route: str, ws: web.WebSocketResponse):
        logger.info(f"A new websocket is opening up on {route}: {ws}")
        self.count_incoming_requests += 1
        return await super().on_websocket(route, ws)

    async def on_message(self, route: str, ws: web.WebSocketResponse, ws_msg_from_client: aiohttp.WSMessage):
        """ Override this function to handle incoming messages from websocket clients. """
        logger.info(f"Received a new websocket message on {route}: {ws_msg_from_client}")
        self.count_websocket_messages += 1

        if ws_msg_from_client.type == web.WSMsgType.TEXT:
            try:
                ws_json: Dict = ws_msg_from_client.json()
                if not isinstance(ws_json, dict):
                    raise Exception("Websocket message was not a dictionary")
            except Exception as ex:
                logger.error(f"Error converting websocket to JSON: {ex}, {ws_msg_from_client.data}")
            else:
                text = ws_json.get("userInput")
                await self.broadcast_json({"replacementText": text})


if __name__ == '__main__':
    main()
