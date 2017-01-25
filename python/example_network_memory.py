#!/usr/bin/env python3
import asyncio
import logging

from experimental import *

logging.basicConfig(level=logging.DEBUG)
logging.getLogger(__name__).setLevel(logging.DEBUG)


def main():
    # example_NetworkMemoryVar()
    example_NetworkMemory()


def example_NetworkMemory():
    loop = asyncio.get_event_loop()
    mem1 = NetworkMemory(local_addr=("225.0.0.1", 9991), remote_addr=("225.0.0.1", 9991), multicast=True)
    # mem2 = NetworkMemory(local_addr=("225.0.0.2", 9992), remote_addr=("225.0.0.1", 9991), multicast=True)

    def when_mem1_changes(var: NetworkMemory, name, old_val, new_val):
        print("mem1 '{}' '{}' changed. Old: {}. New: {}.".format(var, name, old_val, new_val))

    # def when_mem2_changes(var: NetworkMemory, name, old_val, new_val):
    #     print("mem2 '{}' '{}' changed. Old: {}. New: {}.".format(var, name, old_val, new_val))

    mem1.notify(when_mem1_changes)
    # mem2.notify(when_mem2_changes)

    async def prompt():
        while True:
            key = input("Key? ")
            if key != "":
                value = input("Value? ")
                mem1.set(key, value)
            await asyncio.sleep(0.1)

    asyncio.ensure_future(prompt())

    try:
        print("Starting loop...")
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    # transport.close()
    loop.close()


if __name__ == "__main__":
    main()