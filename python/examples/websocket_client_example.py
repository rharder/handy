#!/usr/bin/env python3
"""
Example using WebsocketClient class

Source: https://github.com/rharder/handy

August 2018 - Initial creation
"""
import asyncio
import json
from concurrent import futures

from handy.websocket_client import WebsocketClient

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


def main():
    url = "wss://demos.kaazing.com/echo"
    proxy = None

    async def _run():
        async with WebsocketClient(url, proxy=proxy, verify_ssl=False) as wc:

            # Send a string
            word = "hello"
            print("Sending:", word)
            await wc.send_str(word)
            msg = await wc.get_msg()
            print("Received:", msg.data)
            print()

            # Send json data
            data = dict()
            data["color"] = "blue"
            data["direction"] = "north"
            print("Sending dictionary as json data:", data)
            await wc.send_json(json.dumps(data))
            msg = await wc.get_msg()
            print("Received text string:", msg.data)
            resp_data = json.loads(msg.data)
            print("\tConverted back to dictionary:", resp_data)

            print()
            print("Send several lines at once, and then use a for loop to retrieve all responses:")
            lines = ["Line 1", "Line 2", "Line 3"]
            for line in lines:
                print("Sending:", line)
                await wc.send_str(line)

            print("Entering an async for loop with a 1 second timeout for each subsequent message.")
            print("There should be three websocket messages waiting for us.")
            try:
                async for msg in wc.timeout(1):
                    print("Received:", msg.data)
            except futures.TimeoutError:  # Specifically, concurrent.futures.TimeoutError
                pass

            # print("Entering an async for loop.  The program will stay here indefinitely, waiting for future messages.")
            # async for msg in wc:
            #     print("Received:", msg.data)

        print("Connection closed.")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_run())


if __name__ == "__main__":
    main()
