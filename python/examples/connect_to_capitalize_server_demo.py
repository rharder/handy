import asyncio

import aiohttp

from handy.websocket_client import WebsocketClient
num = 0
clients = []
async def on_connect(client: WebsocketClient):
    clients.append(client)
    # print("Client connected to server.")
    for _ in range(10):
        await client.send_str("hello world")
        await asyncio.sleep(0)


def on_close(client: WebsocketClient):
    global num
    # if num:
    #     print("Closed after {} messages".format(num), client)
    #     num = None


async def on_message(client: WebsocketClient, msg: aiohttp.WSMessage):
    global num
    # if num:
    num += 1
    # print(".", end="", flush=True)
    # print("Client:", client)
    # print("Message:", msg)

for i in range(10):
    WebsocketClient.connect("ws://localhost:9990/cap",
                            on_connect=on_connect,
                            on_close=on_close,
                            on_message=on_message)

# loop = asyncio.ProactorEventLoop()
# asyncio.set_event_loop(loop)
loop = asyncio.get_event_loop()

async def _delay():
    await asyncio.sleep(5)
    for client in clients:
        await client.close()
    print("Number:", num)
# loop.run_forever()
loop.run_until_complete(_delay())