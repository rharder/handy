import asyncio
import ipaddress
import json
import socket
import threading

import struct

from .connector import Connector

class UdpConnector(Connector):
    def __init__(self,
                 local_addr: (str, int) = None,
                 remote_addr: (str, int) = None,
                 loop: asyncio.AbstractEventLoop = None,
                 new_thread: bool = False):
        super().__init__()
        self.local_addr = local_addr
        self.remote_addr = remote_addr
        self.loop = loop
        self.new_thread = new_thread

    def __repr__(self):
        return "{}(local_addr={}, remote_addr={})".format(
            self.__class__.__name__, self.local_addr, self.remote_addr)

    def connect(self, listener, loop=None):
        super().connect(listener, loop)

        if self.new_thread:
            self._connect_on_new_thread(local_addr=self.local_addr, remote_addr=self.remote_addr)
        else:
            self._connect(local_addr=self.local_addr, remote_addr=self.remote_addr, loop=self.loop)

    def _connect(self,
                 local_addr: (str, int) = None,
                 remote_addr: (str, int) = None,
                 loop: asyncio.AbstractEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        if local_addr is None:
            local_addr = ("225.0.0.1", 9999)

        if remote_addr is None:
            self.remote_addr = local_addr
        else:
            self.remote_addr = remote_addr

        local_is_multicast = ipaddress.ip_address(local_addr[0]).is_multicast

        # How to make Python listen to multicast
        if local_is_multicast:
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

            listen = loop.create_datagram_endpoint(lambda: self, sock=_make_sock())
        else:
            listen = loop.create_datagram_endpoint(lambda: self, local_addr=local_addr)

        try:
            self._transport, _ = loop.run_until_complete(listen)
        except RuntimeError as re:
            if "This event loop is already running" in re.args[0]:
                raise RuntimeError("{}.  Did you start the loop before you called connect()?".format(re), re)
            else:
                raise re

    def _connect_on_new_thread(self, local_addr: (str, int), remote_addr: (str, int)):
        """
        Connects the NetworkMemory object to the network.  Will listen on local_addr and send
        updates to remote_addr.

        A new asyncio.BaseEventLoop will be created and run on a new thread to aid in applications
        where there are already other non-compatible event loops, such as tkinter.
        Hopefully a future version of Python will address this incompatibility (current as of Python v3.6).

        :param local_addr:
        :param remote_addr:
        :param local_is_multicast:
        :return:
        """
        ioloop = asyncio.new_event_loop()
        self._connect(local_addr=local_addr, remote_addr=remote_addr, loop=ioloop)
        t = threading.Thread(target=lambda: ioloop.run_forever())
        t.daemon = True
        t.start()

    def send_message(self, msg: dict):
        json_data = json.dumps(msg)
        self.log.debug("Sending to network: {}".format(json_data))
        self._transport.sendto(json_data.encode(), self.remote_addr)


    def connection_made(self, transport):
        self.log.debug("Connection {} made on thread {}".format(transport, threading.get_ident()))
        self._transport = transport
        # self.net_mem.connector_connected(self)
        self.listener.connection_made(self)

    def connection_lost(self, exc):
        self.log.debug("Connection {} lost (Error: {})".format(self._transport, exc))
        self._transport.close()
        self._transport = None
        # self.net_mem.connector_closed(self)
        self.listener.connection_lost(self, exc=exc)

    def datagram_received(self, data, addr):
        self.log.debug("datagram_received from {}: {}".format(addr, data))

        msg = json.loads(data.decode())
        # self.message_received(self, msg)
        self.listener.message_received(self, msg)

    def error_received(self, exc):
        self.log.error("An error was received by {}: {}".format(self, exc))
        # self.net_mem.connector_error(self, exc)
        self.listener.connection_error(self, exc=exc)
