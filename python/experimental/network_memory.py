"""

"""
import asyncio
import json
import socket
import struct
import threading
import time

from handy.bindable_variable import BindableDict

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
        # if not "name" in kwargs:
        #     kwargs["name"] = socket.gethostname()
        super().__init__(**kwargs)

        # Data
        self.remote_addr = None  # type: (str, int)  # remote address is set in connect() function
        self._timestamps = {}  # maps keys to timestamp of change

    def connect(self, local_addr: (str, int), remote_addr: (str, int), multicast=False, loop=None):
        """
        Connects the NetworkMemory object to the network.  Will listen on local_addr and send
        updates to remote_addr.  If local_addr is a multicast address, set the multicast argument to True.
        An asyncio.BaseEventLoop can be provided or else asyncio.get_event_loop() will be used.

        This connect() method must be called when the loop is not yet running.

        :param local_addr:
        :param remote_addr:
        :param multicast:
        :param loop:
        :return:
        """
        loop = loop or asyncio.get_event_loop()
        self.remote_addr = remote_addr

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

            listen = loop.create_datagram_endpoint(lambda: self, sock=_make_sock())
        else:
            listen = loop.create_datagram_endpoint(lambda: self, local_addr=local_addr)

        try:
            self.transport, self.protocol = loop.run_until_complete(listen)
        except RuntimeError as re:
            if "This event loop is already running" in re.args[0]:
                raise RuntimeError("{}.  Did you start the loop before you called connect()?".format(re), re)
            else:
                raise re

    def connect_on_new_thread(self, local_addr: (str, int), remote_addr: (str, int), local_is_multicast=False):
        """
        Connects the NetworkMemory object to the network.  Will listen on local_addr and send
        updates to remote_addr.  If local_addr is a multicast address, set the local_is_multicast
        argument to True.

        A new asyncio.BaseEventLoop will be created and run on a new thread to aid in applications
        where there are already other non-compatible event loops, such as tkinter.
        Hopefully a future version of Python will address this incompatibility (current as of Python v3.6).

        :param local_addr:
        :param remote_addr:
        :param local_is_multicast:
        :return:
        """
        ioloop = asyncio.new_event_loop()
        self.connect(local_addr=local_addr, remote_addr=remote_addr, multicast=local_is_multicast, loop=ioloop)
        t = threading.Thread(target=lambda: ioloop.run_forever())
        t.daemon = True
        t.start()

    # def get(self, name: str, default=None):
    #     """ Return the value associated with a key, or 'default' if not present. """
    #     return super().get(str(name), default)

    def _notify_listeners(self):

        if not self._suspend_notifications:
            self.log.debug("_notify_listeners")
            changes = self._changes.copy()
            timestamp = time.time()
            if len(changes) > 0:
                data = {"update": changes, "timestamp": timestamp, "host": self.name}
                json_data = json.dumps(data)
                self.log.debug("Sending to network: {}".format(json_data))
                self.transport.sendto(json_data.encode(), self.remote_addr)
        super()._notify_listeners()


    # def setz(self, name: str, new_val, force_notify: bool = False, timestamp: float = None):
    #     name = str(name)
    #     timestamp = float(timestamp or time.time())
    #     self._timestamps[name] = timestamp
    #     old_val = self.get(name)
    #
    #     if force_notify or old_val != new_val:
    #         data = {"name": name, "value": new_val, "timestamp": timestamp, "host": self.name}
    #         json_data = json.dumps(data)
    #         self.log.debug("Sending to network: {}".format(json_data))
    #         self.transport.sendto(json_data.encode(), self.remote_addr)
    #
    #     super().set(name, new_val, force_notify=force_notify)

    def connection_made(self, transport):
        self.log.debug("Connection made {} on thread {}".format(transport, threading.get_ident()))
        self.transport = transport

    def datagram_received(self, data, addr):
        self.log.debug("datagram_received from {}: {}".format(addr, data))
        msg = json.loads(data.decode())
        if "update" in msg:
            changes = msg["update"]
            host = str(msg.get("host"))
            timestamp = float(msg.get("timestamp"))
            updates = {}
            for key, old_val, new_val in changes:
                if timestamp > self._timestamps.get(key,0):
                    self.log.debug("Received fresh network data from {}: {} = {}".format(host, key, new_val))
                    updates[key] = new_val
                    self._timestamps[key] = timestamp
                else:
                    self.log.debug("Received stale network data from {}: {} = {}".format(host, key, new_val))
            self.log.debug("Updating network data from {}: {}".format(host, updates))
            self.update(updates)

        # if "name" in msg:
        #     key = str(msg.get("name"))
        #     value = msg.get("value")
        #     host = str(msg.get("host"))
        #     timestamp = int(msg.get("timestamp"))
        #     if timestamp > self._timestamps.get(key, 0):
        #         self.log.debug("Updating with network data from {}: {} = {}".format(host, key, value))
        #         self.set(key, value)
        #     else:
        #         self.log.debug("Received stale network data: {} = {}".format(key, value))
