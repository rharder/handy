"""

"""
import socket
import threading
import time

import asyncio

from handy.bindable_variable import BindableDict
from .connector import Connector

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__date__ = "20 Jan 2017"
__license__ = "Public Domain"


class NetworkMemory(BindableDict):
    def __init__(self, **kwargs):
        if "name" in kwargs:
            self.name = kwargs["name"]
            del kwargs["name"]
        else:
            self.name = socket.gethostname()

        super().__init__(**kwargs)

        # Data
        self._timestamps = {}  # maps keys to timestamp of change
        self._connectors = []  # type: [Connector]

    def connect(self, connector:Connector, loop=None):
        return connector.connect(self, loop=loop)

    def connect_on_new_thread(self, connector):
        ioloop = asyncio.new_event_loop()
        c = self.connect(connector, loop=ioloop)
        t = threading.Thread(target=lambda: ioloop.run_forever())
        t.daemon = True
        t.start()
        return c

    # ########
    # ConnectorListener methods

    def connection_made(self, connector: Connector):
        self.log.info("Connection made: {}".format(connector))
        self._connectors.append(connector)
        connector.message_received = self.message_received

    def connection_lost(self, connector: Connector, exc=None):
        self.log.info("Connection lost. Removing {} ({})".format(connector, exc))
        self._connectors.remove(connector)

    def connection_error(self, connector: Connector, exc=None):
        self.log.warning("Connection error on {}: {}".format(connector, exc))
        print("connector_error", connector, exc)

    def message_received(self, connector: Connector, msg: dict):
        self.log.debug("Message received from {}: {}".format(connector, msg))

        if "update" in msg:
            changes = msg["update"]
            host = str(msg.get("host"))
            timestamp = float(msg.get("timestamp"))
            updates = {}

            for key, old_val, new_val in changes:
                if timestamp > self._timestamps.get(key, 0):
                    self.log.debug("Received fresh network data from {}: {} = {}".format(host, key, new_val))
                    updates[key] = new_val
                    self._timestamps[key] = timestamp
                else:
                    self.log.debug("Received stale network data from {}: {} = {}".format(host, key, new_val))

            self.update(updates)

    # End ConnectorListener methods
    # ########

    def _notify_listeners(self):

        if not self._suspend_notifications:
            changes = self._changes.copy()
            timestamp = time.time()
            if len(changes) > 0:
                data = {"update": changes, "timestamp": timestamp, "host": self.name}
                for connector in self._connectors.copy():
                    connector.send_message(data)
        super()._notify_listeners()

    def close(self):
        for connector in self._connectors.copy():
            connector.close()

#
#
# class NetworkMemory(BindableDict):
#     def __init__(self, **kwargs):
#         if "name" in kwargs:
#             self.name = kwargs["name"]
#             del kwargs["name"]
#         else:
#             self.name = socket.gethostname()
#
#         super().__init__(**kwargs)
#
#         # Data
#         self.remote_addr = None  # type: (str, int)  # remote address is set in connect() function
#         self._transport = None  # type: asyncio.DatagramTransport
#         self._timestamps = {}  # maps keys to timestamp of change
#
#     def connect(self,
#                 local_addr: (str, int) = None,
#                 remote_addr: (str, int) = None,
#                 loop: asyncio.AbstractEventLoop = None):
#         """
#         Connects the NetworkMemory object to the network.  Will listen on local_addr and send
#         updates to remote_addr.
#         An asyncio.BaseEventLoop can be provided or else asyncio.get_event_loop() will be used.
#
#         If no local_addr is given, the multicast address ("225.0.0.1", 9999) will be used for local_addr.
#
#         if no remote_addr is given, local_addr will be used.
#
#         This connect() method must be called when the loop is not yet running.
#
#         :param local_addr:
#         :param remote_addr:
#         :param local_is_multicast:
#         :param loop:
#         :return:
#         """
#         loop = loop or asyncio.get_event_loop()
#
#         if local_addr is None:
#             local_addr = ("225.0.0.1", 9999)
#
#         if remote_addr is None:
#             self.remote_addr = local_addr
#         else:
#             self.remote_addr = remote_addr
#
#         local_is_multicast = ipaddress.ip_address(local_addr[0]).is_multicast
#
#         # How to make Python listen to multicast
#         if local_is_multicast:
#             def _make_sock():
#                 m_addr, port = local_addr
#                 sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#                 sock.bind(('', port))
#                 group = socket.inet_aton(m_addr)
#                 mreq = struct.pack('4sL', group, socket.INADDR_ANY)
#                 sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
#                 sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#                 # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
#                 return sock
#
#             listen = loop.create_datagram_endpoint(lambda: self, sock=_make_sock())
#         else:
#             listen = loop.create_datagram_endpoint(lambda: self, local_addr=local_addr)
#
#         try:
#             self._transport, _ = loop.run_until_complete(listen)
#         except RuntimeError as re:
#             if "This event loop is already running" in re.args[0]:
#                 raise RuntimeError("{}.  Did you start the loop before you called connect()?".format(re), re)
#             else:
#                 raise re
#
#     def connect_on_new_thread(self, local_addr: (str, int), remote_addr: (str, int)):
#         """
#         Connects the NetworkMemory object to the network.  Will listen on local_addr and send
#         updates to remote_addr.
#
#         A new asyncio.BaseEventLoop will be created and run on a new thread to aid in applications
#         where there are already other non-compatible event loops, such as tkinter.
#         Hopefully a future version of Python will address this incompatibility (current as of Python v3.6).
#
#         :param local_addr:
#         :param remote_addr:
#         :param local_is_multicast:
#         :return:
#         """
#         ioloop = asyncio.new_event_loop()
#         self.connect(local_addr=local_addr, remote_addr=remote_addr, loop=ioloop)
#         t = threading.Thread(target=lambda: ioloop.run_forever())
#         t.daemon = True
#         t.start()
#
#     def _notify_listeners(self):
#
#         if not self._suspend_notifications:
#             changes = self._changes.copy()
#             timestamp = time.time()
#             if len(changes) > 0:
#                 data = {"update": changes, "timestamp": timestamp, "host": self.name}
#                 json_data = json.dumps(data)
#                 self.log.debug("Sending to network: {}".format(json_data))
#                 self._transport.sendto(json_data.encode(), self.remote_addr)
#         super()._notify_listeners()
#
#     def close(self):
#         self.log.debug("Connection closed")
#         self._transport.close()
#
#     def connection_made(self, transport):
#         self.log.debug("Connection {} made on thread {}".format(transport, threading.get_ident()))
#         self._transport = transport
#
#     def connection_lost(self, exc):
#         self.log.debug("Connection {} lost (Error: {})".format(self._transport, exc))
#         self._transport = None
#
#     def datagram_received(self, data, addr):
#         self.log.debug("datagram_received from {}: {}".format(addr, data))
#
#         msg = json.loads(data.decode())
#         if "update" in msg:
#             changes = msg["update"]
#             host = str(msg.get("host"))
#             timestamp = float(msg.get("timestamp"))
#             updates = {}
#
#             for key, old_val, new_val in changes:
#                 if timestamp > self._timestamps.get(key, 0):
#                     self.log.debug("Received fresh network data from {}: {} = {}".format(host, key, new_val))
#                     updates[key] = new_val
#                     self._timestamps[key] = timestamp
#                 else:
#                     self.log.debug("Received stale network data from {}: {} = {}".format(host, key, new_val))
#             self.log.debug("Updating network data from {}: {}".format(host, updates))
#             self.update(updates)
#
#     def error_received(self, exc):
#         self.log.error("An error was received by {}: {}".format(self, exc))
