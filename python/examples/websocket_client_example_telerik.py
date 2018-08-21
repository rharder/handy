#!/usr/bin/env python3
"""
Example using WebsocketClient class

Source: https://github.com/rharder/handy

August 2018 - Initial creation
"""
import asyncio
import pprint
import webbrowser

from handy.websocket_client import WebsocketClient

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__license__ = "Public Domain"


def main():
    web_url = "https://demos.telerik.com/kendo-ui/grid/web-socket"
    ws_url = "wss://kendoui-ws-demo.herokuapp.com/"
    proxy = None

    webbrowser.open(web_url)

    async def _run():
        async with WebsocketClient(ws_url, proxy=proxy, verify_ssl=False) as wc:
            print("From the web page that opened, make changes to the data, and watch those pushed to the console.")
            print(web_url)
            print("Entering an async for loop.  The program will stay here indefinitely, waiting for future messages.")

            async for msg in wc:
                data = msg.json()
                print("Received:", pprint.pformat(data))

        print("Connection closed.")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_run())


if __name__ == "__main__":
    main()
