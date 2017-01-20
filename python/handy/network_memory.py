"""

"""
import asyncio
import json
import logging

from .bindable_variable import Var

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"
__date__ = "20 Jan 2017"
__license__ = "Public Domain"

class NetworkMemory:
    def __init__(self, local_addr, remote_addr, loop=None):
        self.log = logging.getLogger(__name__)
        self.local_addr = local_addr
        self.remote_addr = remote_addr
        self._value = {}
        # self.name = "tbd"
        self.loop = loop or asyncio.get_event_loop()

        self.log.debug("Created {}".format(self))

        listen = self.loop.create_datagram_endpoint(lambda: self, local_addr=self.local_addr)
        self.transport, self.protocol = self.loop.run_until_complete(listen)  # Pause to connect
        self.log.debug("self.transport: {}".format(self.transport))

    def get(self, name, default=None):
        return self._value.get(name, default)

    def set(self, name, new_val):
        self._value[name] = new_val
        data = {"name":name, "value":new_val}
        json_data = json.dumps(data)
        self.log.debug("Sending to network: {}".format(json_data))
        self.transport.sendto(json_data.encode(), self.remote_addr)


    def connection_made(self, transport):
        self.log.debug("Connection made {}".format(transport))
        self.transport = transport

    def datagram_received(self, data, addr):
        self.log.debug("datagram_received: {}".format(data))
        msg = json.loads(data.decode())
        if "name" in msg:
            name = msg.get("name")
            value = msg.get("value")
            self.log.debug("Updating with network data: {} = {}".format(name, value))
            self.set(name, value)
            print("self._value:", self._value)

class NetworkMemoryVar(Var):
    def __init__(self, addr, loop = None, **kwargs):
        super().__init__(**kwargs)
        self.addr = addr
        self.loop = loop or asyncio.get_event_loop()

        listen = self.loop.create_datagram_endpoint(self._protocol, local_addr=addr)
        self.transport, self.protocol = self.loop.run_until_complete(listen)  # Pause to connect
        self.log.debug("self.transport: {}".format(self.transport))

        self.notify(self._update_network)

    def _update_network(self, var, old_val, new_val):
        data = {"name":self.name, "value":new_val}
        json_data = json.dumps(data)
        self.log.debug("Sending to network: {}".format(json_data))
        self.transport.sendto(json_data.encode(), self.addr)

    def _protocol(self):
        return self

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.log.debug("datagram_received {} {}".format(self, data))
        msg = json.loads(data.decode())
        if msg.get("name") == self.name:
            value = msg.get("value")
            self.log.debug("Updating with network data: {}".format(value))
            self.value = value


