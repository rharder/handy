"""
Problem solved in aiohttp v1.3.0.  I was on 1.2.0.
"""
import asyncio
import aiohttp


# Closing the echo.websocket.org connection works as expected
# Closing the stream.pushbullet.com connection hangs

async def run():
    session = aiohttp.ClientSession()
    API_KEY = "RrFnc1xaeQXnRrr2auoGA1e8pQ8MWmMF"
    async with session.ws_connect('wss://stream.pushbullet.com/websocket/' + API_KEY) as ws:
    # async with session.ws_connect("wss://echo.websocket.org") as ws:
        ws.send_json({"hello": "world"})

        async def _timeout():
            await asyncio.sleep(2)
            print('closing ... ', end="", flush=True)
            await ws.close()
            print('... closed. Should see "broke out of ..." messages next')

        asyncio.get_event_loop().create_task(_timeout())

        async for ws_msg in ws:
            print("ws_msg:", ws_msg)

        print("broke out of async for loop")
    print("broke out of async with")
    session.close()


loop = asyncio.get_event_loop()
loop.run_until_complete(run())
print("goodbye")
