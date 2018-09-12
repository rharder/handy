import asyncio

import aiohttp

from handy.websocket_client import WebsocketClient


async def on_connect(client: WebsocketClient):
    print("Connected to client. Saying hi...")
    await client.send_str("hello world")


def on_close(client: WebsocketClient):
    print("Closed!", client)


def on_message(client: WebsocketClient, msg: aiohttp.WSMessage):
    print("Client:", client)
    print("Message:", msg)


WebsocketClient.connect("ws://localhost:9990/cap",
                        on_connect=on_connect,
                        on_close=on_close,
                        on_message=on_message)

loop = asyncio.get_event_loop()
loop.run_forever()
