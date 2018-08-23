#!/usr/bin/env python3
import asyncio
import webbrowser

from aiohttp import web


async def setup():
    app = web.Application()
    app.router.add_get("/", ws_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", port=9999)
    await site.start()


async def ws_handler(request: web.BaseRequest):
    ws = web.WebSocketResponse()
    try:
        await ws.prepare(request)
        await ws.send_str("Welcome to this demo.")
        await ws.send_str("Trying forcing closed this connection with something like TCPView:")
        await ws.send_str("https://docs.microsoft.com/en-us/sysinternals/downloads/tcpview")
        while not ws.closed:
            ws_msg = await ws.receive()
            print("Received:", ws_msg)
    except Exception as ex:
        print("I cannot catch the Exception when connection is forcibly closed.", flush=True)
        print("Exception", ex, flush=True)
        ex.with_traceback()
    finally:
        print("I am never run when connection is forcibly closed.", flush=True)

    return ws


webbrowser.open("http://www.websocket.org/echo.html?location=ws://localhost:9999")
loop = asyncio.get_event_loop()
loop.create_task(setup())
loop.run_forever()


"""
## Long story short

When the TCP connection to my websocket server is forcibly closed (outside Python's control, such as with TCPView), there is an infinite loop of Exceptions that my user-level code cannot catch.

## Expected behaviour

I would expect to get a connection closed message or exception as with other kinds of service interruptions.

## Actual behaviour

I get an infinite loop of exceptions that cannot be caught.

    Exception in callback BaseSelectorEventLoop._read_from_self()
    handle: <Handle BaseSelectorEventLoop._read_from_self()>
    Traceback (most recent call last):
      File "C:\Python37-32\lib\asyncio\events.py", line 88, in _run
        self._context.run(self._callback, *self._args)
      File "C:\Python37-32\lib\asyncio\selector_events.py", line 125, in _read_from_self
        data = self._ssock.recv(4096)
    ConnectionResetError: [WinError 10054] An existing connection was forcibly closed by the remote host

## Steps to reproduce

The code below is a smallest-representation of the problem.  Run the websocket server on localhost, and connect to it with a client such as the tool at http://www.websocket.org/echo.html?location=ws://localhost:9999 .  Then forcibly close the TCP connection using a tool like TCPView to simulate an OS-level event.

    #!/usr/bin/env python3
    import asyncio
    import webbrowser
    
    from aiohttp import web
    
    
    async def setup():
        app = web.Application()
        app.router.add_get("/", ws_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", port=9999)
        await site.start()
    
    
    async def ws_handler(request: web.BaseRequest):
        ws = web.WebSocketResponse()
        try:
            await ws.prepare(request)
            await ws.send_str("Welcome to this demo.")
            await ws.send_str("Trying forcing closed this connection with something like TCPView:")
            await ws.send_str("https://docs.microsoft.com/en-us/sysinternals/downloads/tcpview")
            while not ws.closed:
                ws_msg = await ws.receive()
                print("Received:", ws_msg)
        except Exception as ex:
            print("I cannot catch the Exception when connection is forcibly closed.", flush=True)
            print("Exception", ex, flush=True)
            ex.with_traceback()
        finally:
            print("I am never run when connection is forcibly closed.", flush=True)
    
        return ws
    
    
    webbrowser.open("http://www.websocket.org/echo.html?location=ws://localhost:9999")
    loop = asyncio.get_event_loop()
    loop.create_task(setup())
    loop.run_forever()



## Your environment

- Windows 10
- aiohttp v3.3.2
- Python 3.7 32bit

"""