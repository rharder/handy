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
import tkinter as tk
import webbrowser

import aiohttp
from aiohttp import web, WSMsgType

from handy.tk_asyncio_base import TkAsyncioBaseApp
from handy.tkinter_tools import BindableTextArea
from handy.websocket_server import WebServer, WebHandler, WebsocketHandler

__author__ = "Robert Harder"


def main():
    tk_root = tk.Tk()
    MainApp(tk_root)
    tk_root.mainloop()


class MainApp(TkAsyncioBaseApp):
    def __init__(self, root: tk.Tk):
        super().__init__(root)
        self.root = root
        root.title("Websocket Example")
        self.log = logging.getLogger(__name__)

        # Data
        self.port_var: tk.IntVar = tk.IntVar()
        self.detail_var: tk.StringVar = tk.StringVar()
        self.server: WebServer = None
        self.socket_handler: MyWebSocketHandler = None
        self.web_handler: MyWebPageHandler = None

        # View / Control
        self.create_widgets(self.root)

        # Connections
        self.port_var.set(9999)
        self.detail_var.trace("w", self.detail_var_changed)
        self.detail_var.set("")

    def create_widgets(self, parent: tk.Misc):
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
        port = int(self.port_var.get())
        self.server = WebServer(port=port)
        self.socket_handler = MyWebSocketHandler(self)
        self.web_handler = MyWebPageHandler(port=port)
        self.server.add_route("/", self.web_handler)
        self.server.add_route("/ws", self.socket_handler)

        async def _connect():
            print("Starting server...")
            await self.server.start()
            self.detail_var.set(f"Server started on port {self.server.port}")

            # Just for fun...
            await asyncio.sleep(10)
            detail = self.detail_var.get() + "\nall your base are belong to us\n"
            self.detail_var.set(detail)

        self.io(_connect())  # Schedule on asyncio loop

    def open_webbrowser_clicked(self):
        port = int(self.port_var.get())
        url = "http://localhost:{}/".format(port)
        webbrowser.open(url)

    def detail_var_changed(self, _, __, ___):
        # When someone types in the box, we'll send the text over the network
        detail = self.detail_var.get()
        if self.socket_handler:
            msg = {"detail": detail}
            self.io(self.socket_handler.broadcast_json(msg))


class MyWebPageHandler(WebHandler):
    HTML1 = """<html>
    <head>
        <title>My Web Page</title>
        <script type="text/javascript">
    var connection = null;
    var WebSocket = WebSocket || MozWebSocket;
    var port = """  # Insert port number here
    HTML2 = """;

    function connect() {
      var serverUrl = "ws://" + window.location.hostname + ":" + port + "/ws";
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

    def __init__(self, port: int):
        super().__init__()
        self.port = port

        self.html = self.HTML1 + str(port) + self.HTML2

    async def on_incoming_http(self, route: str, request: web.BaseRequest):
        return web.Response(text=self.html, content_type="text/html")


class MyWebSocketHandler(WebsocketHandler):

    def __init__(self, parent: MainApp, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.parent = parent

    async def on_websocket(self, route: str, ws: web.WebSocketResponse):
        # First intercept new connection and send the current contents
        detail = self.parent.detail_var.get()
        self.parent.tk(self.parent.detail_var.set, detail + "\nConnected.")
        msg = {"detail": detail}
        await ws.send_str(json.dumps(msg))

        # Now wait for future messages
        await super().on_websocket(route, ws)

    async def on_message(self, route: str, ws: web.WebSocketResponse, ws_msg_from_client: aiohttp.WSMessage):
        if ws_msg_from_client.type == WSMsgType.TEXT:
            msg = ws_msg_from_client.json()
            self.parent.tk(self.parent.detail_var.set, msg.get("detail"))  # Schedule on gui thread
        elif ws_msg_from_client.type == WSMsgType.CLOSE:
            # Two ways two detect a closing
            txt = self.parent.detail_var.get() + "\nDisconnected."
            self.parent.tk(self.parent.detail_var.set, txt)

    async def on_close(self, route: str, ws: web.WebSocketResponse):
        # Two ways to detect a closing
        txt = self.parent.detail_var.get() + "\nDisconnected."
        self.parent.tk(self.parent.detail_var.set, txt)


if __name__ == "__main__":
    main()
