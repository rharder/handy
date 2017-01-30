#!/usr/bin/env python3
import asyncio
import logging

import sys

from experimental import *
# from netmem.network_memory import NetworkMemoryC, UdpConnector
import netmem

logging.basicConfig(level=logging.ERROR)
logging.getLogger(__name__).setLevel(logging.DEBUG)


def main():
    # example_NetworkMemoryVar()
    example_NetworkMemory()


def example_NetworkMemory():
    loop = asyncio.get_event_loop()
    mem1 = netmem.NetworkMemoryC()
    mem2 = netmem.NetworkMemoryC()

    def when_mem1_changes(var: netmem.NetworkMemoryC, name, old_val, new_val):
        print("mem1 '{}' '{}' changed. Old: {}. New: {}.".format(var, name, old_val, new_val))

    def when_mem2_changes(var: netmem.NetworkMemoryC, name, old_val, new_val):
        print("mem2 '{}' '{}' changed. Old: {}. New: {}.".format(var, name, old_val, new_val))

    mem1.add_listener(when_mem1_changes)
    mem2.add_listener(when_mem2_changes)

    mem1.connect(netmem.UdpConnector(local_addr=("225.0.0.1", 9991), remote_addr=("225.0.0.2", 9992)))
    mem2.connect(netmem.UdpConnector(local_addr=("225.0.0.2", 9992), remote_addr=("225.0.0.1", 9991)))

    async def prompt():
        while True:
            key = input("Key? ")
            value = input("Value? ")
            mem1.set(key, value)
            await asyncio.sleep(0.1)

    asyncio.ensure_future(prompt())

    try:
        print("Starting loop...")
        loop.run_forever()
    except KeyboardInterrupt:
        sys.exit(1)
    # transport.close()
    loop.close()


if __name__ == "__main__":
    main()
