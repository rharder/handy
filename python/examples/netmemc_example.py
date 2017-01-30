#!/usr/bin/env python3
import asyncio
import logging

import sys

from experimental import *
# from netmem.network_memory import NetworkMemoryC, UdpConnector
import netmem
from netmem.logging_connector import LoggingConnector
from netmem.websocket_connector import WsServerConnector, WsClientConnector

logging.basicConfig(level=logging.DEBUG)
logging.getLogger(__name__).setLevel(logging.DEBUG)


def main():
    # example_NetworkMemoryVar()
    example_NetworkMemory()


def example_NetworkMemory():
    loop = asyncio.get_event_loop()
    mem1 = netmem.NetworkMemory()
    mem2 = netmem.NetworkMemory()
    mem3 = netmem.NetworkMemory()

    def when_mem1_changes(var: netmem.NetworkMemory, name, old_val, new_val):
        print("mem1 '{}' '{}' changed. Old: {}. New: {}.".format(var, name, old_val, new_val))

    def when_mem2_changes(var: netmem.NetworkMemory, name, old_val, new_val):
        print("mem2 '{}' '{}' changed. Old: {}. New: {}.".format(var, name, old_val, new_val))

    mem1.add_listener(when_mem1_changes)
    mem2.add_listener(when_mem2_changes)

    # mem1.connect(netmem.UdpConnector(local_addr=("225.0.0.1", 9991), remote_addr=("225.0.0.2", 9992)))
    # mem2.connect(netmem.UdpConnector(local_addr=("225.0.0.2", 9992), remote_addr=("225.0.0.1", 9991)))
    # mem1.connect(LoggingConnector())
    # wss = mem1.connect(WsServerConnector(port=8080))
    mem2.connect(WsClientConnector(url="ws://localhost:8080/"))
    # mem3.connect(WsClientConnector(url=wss.url))

    async def prompt():
        while True:
            key = input("Key? ")
            if key == "":
                await asyncio.sleep(0.5)
                continue
            value = input("Value? ")
            mem1.set(key, value)
            await asyncio.sleep(0.5)

    # asyncio.ensure_future(prompt())

    try:
        print("Starting loop...")
        loop.run_forever()
    except KeyboardInterrupt:
        sys.exit(1)
    # transport.close()
    loop.close()


if __name__ == "__main__":
    main()
