#!/usr/bin/env python3
"""
An example of how to use asyncio event loops and tkinter event loops in the same program.

Discussed here: http://blog.iharder.net/2017/02/03/python-asyncio-and-tkinter-together/
UDP Version: http://pastebin.com/PeHHRR4E
TCP Version: http://pastebin.com/ZGeDULR9
"""
import asyncio
import json
import logging
import threading
import tkinter as tk
import webbrowser
from functools import partial

import aiohttp
from aiohttp import web

from handy.tkinter_tools import BindableTextArea
from handy.websocket_server import WebServer, WebHandler, WebsocketHandler

__author__ = "Robert Harder"


def main():
    tk_root = tk.Tk()
    MainApp(tk_root)
    tk_root.mainloop()


class MainApp:
    def __init__(self, root):
        self.window = root
        root.title("Websocket Example")
        self.log = logging.getLogger(__name__)

        # Data
        self.port_var = tk.IntVar()
        self.detail_var = tk.StringVar()
        self.ioloop = None  # type: asyncio.BaseEventLoop
        self.server = None  # type: WebServer
        self.socket_handler = None  # type: MyWebSocketHandler
        self.web_handler = None  # type: MyWebPageHandler

        # View / Control
        self.create_widgets(self.window)

        # Connections
        self.port_var.set(9999)
        self.detail_var.trace("w", self.detail_var_changed)
        self.detail_var.set("")

        # Thread that will handle io loop
        def _run(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        self.ioloop = asyncio.new_event_loop()  # type: asyncio.BaseEventLoop
        threading.Thread(target=partial(_run, self.ioloop), daemon=True).start()

    def create_widgets(self, parent: tk.Frame):
        # Port
        lbl_port = tk.Label(parent, text="Port:")
        lbl_port.grid(row=0, column=0)
        txt_port = tk.Entry(parent, textvariable=self.port_var)
        txt_port.grid(row=0, column=1)

        # Buttons
        cmd_server = tk.Button(parent, text="Start Server", command=self.start_server_clicked)
        cmd_server.grid(row=0, column=2)
        cmd_openbrowser = tk.Button(parent, text="Open Web Browser", command=self.open_webbrowser_clicked)
        cmd_openbrowser.grid(row=0, column=3)

        # Output
        txt_detail = BindableTextArea(parent, textvariable=self.detail_var, width=40, height=20)
        txt_detail.grid(row=1, column=0, columnspan=4, sticky="NSEW")
        parent.grid_rowconfigure(1, weight=1)

    def start_server_clicked(self):
        print("start")

        self.server = WebServer(port=int(self.port_var.get()))
        self.socket_handler = MyWebSocketHandler(self)
        self.web_handler = MyWebPageHandler()
        self.server.add_route("/", self.web_handler)
        self.server.add_route("/ws", self.socket_handler)

        async def _connect():
            print("Starting server...")
            await self.server.start()
            self.detail_var.set("Connected")

            await asyncio.sleep(10)
            # await self.socket_handler.broadcast_text("all your base are belong to us")
            await asyncio.sleep(1)
            # self.server.close_requests()
            # await self.server.close()
            # await self.socket_handler.close_websockets()

        asyncio.run_coroutine_threadsafe(_connect(), self.ioloop)

    def open_webbrowser_clicked(self):
        port = int(self.port_var.get())
        url = "http://www.websocket.org/echo.html?location=ws://localhost:{}/ws".format(port)
        url = "http://localhost:{}/".format(port)
        webbrowser.open(url)

    def detail_var_changed(self, _, __, ___):
        # When someone types in the box, we'll send the text over the network
        detail = self.detail_var.get()
        if self.socket_handler:
            msg = {"detail": detail}
            asyncio.run_coroutine_threadsafe(self.socket_handler.broadcast_json(msg), self.ioloop)


class MyWebPageHandler(WebHandler):
    HTML = """<html>
<head>
    <title>My Web Page</title>
    <script type="text/javascript">
var connection = null;
var WebSocket = WebSocket || MozWebSocket;

function connect() {
  var serverUrl = "ws://" + window.location.hostname + ":9999/ws";
  connection = new WebSocket(serverUrl);

  connection.onmessage = function(evt) {
    var msg = JSON.parse(evt.data);
    var detail = msg.detail;
    document.getElementById("detail").value = detail;
  };
  
  connection.onclose = function(evt) {
    document.getElementById("detail").value = 
      document.getElementById("detail").value + "\\n\\nDisconnected.";
  };
  
}

function send() {
  var msg = { detail: document.getElementById("detail").value };
  connection.send(JSON.stringify(msg));
}

function handleKey(evt) {
  if (evt.keyCode === 13 || evt.keyCode === 14) {
      send();
  }
}
    </script>
</head>
<body onload="connect()">
<p>Type and hit Enter to send text</p>
<textarea id="detail" onkeyup="handleKey(event)" rows="10" cols="40"></textarea>
</body>
</html>
"""

    async def on_incoming_http(self, route: str, request: web.BaseRequest):
        # await asyncio.sleep(12)
        return web.Response(text=self.HTML, content_type="text/html")


class MyWebSocketHandler(WebsocketHandler):

    def __init__(self, parent: MainApp, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.parent = parent

    async def on_websocket(self, route: str, ws: web.WebSocketResponse):
        # First send the current contents
        detail = self.parent.detail_var.get()
        msg = {"detail": detail}
        await ws.send_str(json.dumps(msg))

        # Now wait for future messages
        await super().on_websocket(route, ws)

    async def on_message(self, route: str, ws: web.WebSocketResponse, ws_msg_from_client: aiohttp.WSMessage):
        # print("Received websocket message", ws_msg_from_client)
        msg = ws_msg_from_client.json()
        self.parent.detail_var.set(msg.get("detail"))


if __name__ == "__main__":
    main()
