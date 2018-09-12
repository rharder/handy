#!/usr/bin/env python3
"""
Illustrates using the streaming response in aiohttp.
"""
import asyncio
import datetime
import random
import ssl
import sys
import time
import traceback
import webbrowser

import aiohttp
from aiohttp import web

from handy.websocket_server import WebsocketHandler, WebServer, WebHandler

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


def main():
    # Create servers
    port = 443

    # sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # sslcontext = ssl.create_default_context()
    sslcontext.load_cert_chain('server.crt', 'server.key')

    server = WebServer(port=port, ssl_context=sslcontext)
    stream_handler = StreamResponseHandler()
    server.add_route("/", stream_handler)

    # Queue their start operation
    loop = asyncio.get_event_loop()
    loop.create_task(server.start())

    # Open web pages to test them
    url = "https://localhost:{}/".format(port)
    webbrowser.open(url)

    # Run event loop
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("keyboard interrupt")
        loop.run_until_complete(server.shutdown())

        loop.close()
    print("loop.run_forever() must have finished")


class StreamResponseHandler(WebHandler):
    HEADER = """<!doctype html>
<html>
</head>
<body>
<h1>Items Appear Over Time</h1>
<p>Some web browsers will display HTML content as it arrives in chunks.
Others may not show you anything until all the data arrives.</p>
<ol>
"""
    FOOTER = """
</ol>
</body>
</html>"""

    async def on_incoming_http(self, route: str, request: web.BaseRequest):
        resp = web.StreamResponse(status=200,
                                  reason='OK',
                                  headers={'Content-Type': 'text/html'})

        # The StreamResponse is a FSM. Enter it with a call to prepare.
        await resp.prepare(request)

        await resp.write(self.HEADER.encode())
        for i in range(10):
            await resp.write("<li>Item {}</li>".format(i + 1).encode())
            await asyncio.sleep(1)
        await resp.write(self.FOOTER.encode())

        return resp


if __name__ == "__main__":
    main()
