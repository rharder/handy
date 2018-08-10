"""
Problem solved in aiohttp v1.3.0.  I was on 1.2.0.
"""
import asyncio
import logging
import sys
import weakref
import webbrowser

import aiohttp
from aiohttp import web

class BareBonesExample:

    async def start(self):
        self._stopping = False
        route = "/"
        port = 8080
        self.app = web.Application()
        # print("App", self.app, id(self.app))
        self.app['websockets'] = weakref.WeakSet()
        self.app.router.add_get(route, self.websocket_handler)
        self.app.on_shutdown.append(self._on_shutdown)

        self.runner = web.AppRunner(self.app)
        # print("runner", self.runner, id(self.runner))
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, 'localhost', port)
        # print("site", self.site, id(self.site))
        await self.site.start()

    async def websocket_handler(self, request: web.BaseRequest):

        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.app['websockets'].add(ws)
        # Echo two replies to the websocket and then kill the server
        # to demonstrate the maximum recursion error and/or runner not registered error.
        try:
            counter = 0
            while counter < 2:
                # Echo
                ws_msg = await ws.receive()
                counter += 1
                # print("Received Message #{}:".format(counter), ws_msg)
                await ws.send_str("Echoing back: {}".format(ws_msg))

            # Close server, two ways
            # Using await self.runner.cleanup() gives a recursion error totally outside my code
            await self.runner.cleanup()
            await self.close()

            # Creating a separate task avoid the recursion error but gives an error like so:
            # RuntimeError: Site <aiohttp.web_runner.TCPSite object at 0x06315430> is not registered in runner <aiohttp.web_runner.AppRunner object at 0x0632F4B0>
            # asyncio.create_task(self.runner.cleanup())
            # asyncio.create_task(self.close())
        finally:
            self.app['websockets'].discard(ws)

        return ws

    async def close(self):
        if not self._stopping:
            self._stopping = True
            await self.site.stop()
        # await self.runner.cleanup()


    async def _on_shutdown(self, app):
        for ws in set(app['websockets']):  # type: web.WebSocketResponse
            await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown')


        #
        # self.app['websockets'].add(ws)
        # if len(set(self.app['websockets'])) > 1:
        #     print("Already got a connection")
        #     await self.runner.cleanup()
        #     return
        #
        # async def _regular_interval():
        #     await asyncio.sleep(3)
        #     await self.close()
        #     print("Exiting _regular_interval...")
        # task = asyncio.create_task(_regular_interval())
        #
        # counter = 0
        # try:
        #     while counter < 2:
        #         ws_msg = await ws.receive()
        #         counter += 1
        #         print("Received Message #{}:".format(counter), ws_msg)
        #
        #     # print("Closing socket...")
        #     # await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown')
        #     # print("closed, supposedly")
        #     print("Calling self.runner.cleanup")
        #     # await self.runner.cleanup()
        #     await self.close()
        #     print("self.runner.cleanup completed")
        # finally:
        #     self.app['websockets'].discard(ws)
        #
        # return ws

class WsServer(object):
    def __init__(self, port: int = 8000, route: str = "/"):
        """
        Create a new WsServer that will listen on the given port and at the given route.
        The default port is 8000, and the default route is /, ie, by default the server
        will listen at http://localhost:8000/

        :param port: The port on which to listen
        :param route: The route at which to listen
        """
        super().__init__()
        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        # Passed parameters
        self.port = port
        self.route = route

        # Internal use
        # self.websockets = []  # type: [web.WebSocketResponse]
        # self.loop = None  # type: asyncio.AbstractEventLoop
        self.app = None  # type: web.Application
        self.site = None  # type: web.TCPSite
        self.runner = None  # type: web.AppRunner
        self._running = False  # type: bool
        self._shutting_down = False  # type: bool

    def __str__(self):
        return "{}({}:{})".format(self.__class__.__name__, self.port, self.route)

    @property
    def running(self):
        # print("running = false but really", self._running)
        # return False
        return self._running


    async def close(self):
        if not self._shutting_down:
            self._shutting_down = True
            # await self.runner.cleanup()
            asyncio.create_task(self.runner.cleanup())
        else:
            print("Already shutting down, says self.close()", flush=True)

    async def _on_shutdown(self, app):
        print("_on_shutdown", app, flush=True)
        await self.close_websockets()
        self._running = False

        print("Exiting system...")
        loop = asyncio.get_event_loop()
        # loop.stop()
        # asyncio.create_task(asyncio.sleep(1))

    async def close_websockets(self):
        print("close_websockets called", flush=True)
        for ws in set(self.app['websockets']):  # type: web.WebSocketResponse
            print("Closing websocket", ws, flush=True)
            await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown')
            # ws.cancel()
            print("Closed", ws, flush=True)


    async def start(self, port: int = None, route: str = None):
        """
        Starts the websocket server and begins listening on a given port and at
        a given route.  These values can be provided in the __init__() constructor
        or at the time start() is called.  The parameters given in start() will
        override whatever was provided in the constructor.

        :param port: The port on which to listen (overrides the constructor values)
        :param route: The route at which to lsiten (overrides the constructor values)
        :return: None
        """
        self.route = route or self.route
        self.port = port or self.port

        self.app = web.Application()
        self.app['websockets'] = weakref.WeakSet()
        self.app.router.add_get(self.route, self.websocket_handler)
        self.app.on_shutdown.append(self._on_shutdown)

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, 'localhost', port=self.port)
        await self.site.start()
        self._running = True

    async def websocket_handler(self, request: web.BaseRequest):
        """
        Handles the incoming websocket client connection and calls on_websocket()
        in order to hand off control to subclasses of the server.

        If this server is being attached to an existing web.Application(), this function
        may be added as a route to that app without using this class's start() and close() functions,
        although you can still use the close_websockets() function (and should) when closing
        your web.Application().
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_str("Connected: {}".format(str(ws)))

        # self.websockets.append(ws)
        self.app['websockets'].add(ws)
        try:
            await self.on_websocket(ws)
        finally:
            self.app['websockets'].discard(ws)
        return ws


    async def on_websocket(self, ws: web.WebSocketResponse):
        """
        Override this function if you want to handle new incoming websocket clients.
        The default behavior is to listen indefinitely for incoming messages from clients
        and call on_message() with each one.
        """
        while True:
            try:
                ws_msg = await ws.receive()  # type: aiohttp.WSMessage
            except RuntimeError as e:  # Socket closing throws RuntimeError
                # print("RuntimeError - did socket close?", e, flush=True)
                break
            else:
                # Call on_message() if it got something
                try:
                    await self.on_message(ws=ws, ws_msg_from_client=ws_msg)
                except RuntimeError as e:
                    # Probably the socket is closing
                    # Exception seen during development:
                    #   This event loop is already running
                    # print("await on_message aborted")
                    break

        print("on_websocket last line", self)



    async def on_message(self, ws: web.WebSocketResponse, ws_msg_from_client: aiohttp.WSMessage):
        """ Override this function to handle incoming messages from websocket clients. """
        pass

    # async def close(self):
    #     await self.runner.cleanup()
    #
    # async def _on_shutdown(self, app):
    #     print("_on_shutdown", app, flush=True)
    #     await self.close_websockets()
    #
    #     # print("Exiting system...")
    #     # loop = asyncio.get_event_loop()
    #     # loop.stop()
    #
    # async def close_websockets(self):
    #     print("close_websockets called")
    #     for ws in set(self.app['websockets']):  # type: web.WebSocketResponse
    #         print("Closing websocket", ws)
    #         await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown')
    #         print("Closed", ws)


class WsExample(WsServer):

    async def on_websocket(self, ws: web.WebSocketResponse):


        counter = 0
        while True:
            counter += 1
            if counter > 2:
                await self.close()
                # asyncio.create_task(self.close())
                break
            try:
                ws_msg = await ws.receive()  # type: aiohttp.WSMessage
            except RuntimeError as e:  # Socket closing throws RuntimeError
                print("RuntimeError - did socket close?", e, flush=True)
                break
            else:
                # Call on_message() if it got something
                await self.on_message(ws=ws, ws_msg_from_client=ws_msg)
        print("on_websocket last line", self)

    async def on_message(self, ws: web.WebSocketResponse, ws_msg_from_client: aiohttp.WSMessage):
        """ Override this function to handle incoming messages from websocket clients. """
        pass
        cap = str(ws_msg_from_client.data).upper()
        if "BAR" in cap:
            await self.close()
            # asyncio.create_task(self.close())



port = 8080
url = "http://www.websocket.org/echo.html?location=ws://localhost:{}".format(port)
webbrowser.open(url)
loop = asyncio.get_event_loop()

# server = WsServer(port=8080)
server = WsExample(port=8080)
# server = BareBonesExample()
loop.create_task(server.start())

loop.run_forever()
print("goodbye")
