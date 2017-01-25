"""

"""
import asyncio
import json
import socket
import struct
import time

from handy.bindable_variable import BindableDict

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__date__ = "20 Jan 2017"
__license__ = "Public Domain"


class NetworkMemory(BindableDict):
    def __init__(self, local_addr: (str, int), remote_addr: (str, int),
                 loop: asyncio.BaseEventLoop = None, multicast=False, **kwargs):
        super().__init__(**kwargs)

        # Data
        self.local_addr = local_addr
        self.remote_addr = remote_addr
        self.loop = loop or asyncio.get_event_loop()
        self._timestamps = {}  # maps keys to timestamp of change

        # Server
        if multicast:
            def _make_sock():
                m_addr, port = local_addr
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(('', port))
                group = socket.inet_aton(m_addr)
                mreq = struct.pack('4sL', group, socket.INADDR_ANY)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                return sock

            listen = self.loop.create_datagram_endpoint(lambda: self, sock=_make_sock())
        else:
            listen = self.loop.create_datagram_endpoint(lambda: self, local_addr=self.local_addr)
        self.transport, self.protocol = self.loop.run_until_complete(listen)  # Pause to connect
        self.log.debug("self.transport: {}".format(self.transport))

    def get(self, name: str, default=None):
        return super().get(str(name), default)

    def set(self, name: str, new_val, force_notify: bool = False, timestamp: float = None):
        name = str(name)
        timestamp = float(timestamp or time.time())
        self._timestamps[name] = timestamp
        old_val = self.get(name)

        if force_notify or old_val != new_val:
            data = {"name": name, "value": new_val, "timestamp": timestamp}
            json_data = json.dumps(data)
            self.log.debug("Sending to network: {}".format(json_data))
            self.transport.sendto(json_data.encode(), self.remote_addr)

        super().set(name, new_val, force_notify=force_notify)

    def connection_made(self, transport):
        self.log.debug("Connection made {}".format(transport))
        self.transport = transport

    def datagram_received(self, data, addr):
        self.log.debug("datagram_received {}: {}".format(self, data))
        msg = json.loads(data.decode())
        if "name" in msg:
            name = str(msg.get("name"))
            value = msg.get("value")
            timestamp = int(msg.get("timestamp"))
            if timestamp > self._timestamps.get(name, 0):
                self.log.debug("Updating with network data: {} = {}".format(name, value))
                self.set(name, value)
            else:
                self.log.debug("Received stale network data: {} = {}".format(name, value))