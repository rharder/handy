#!/usr/bin/env python3
import asyncio
import logging

import sys

sys.path.append("..")
from handy.network_memory import NetworkMemory

# logging.basicConfig(level=logging.DEBUG)
# logging.getLogger(__name__).setLevel(logging.DEBUG)


def main():
    net_mem_monitor()


def net_mem_monitor():
    mem = NetworkMemory()

    def _when_mem_changes(var: NetworkMemory, key, old_val, new_val):
        print(mem)

    mem.add_listener(_when_mem_changes)
    # mem.add_listener(lambda *kargs:print(mem))

    mem.connect(local_addr=("225.0.0.2", 9992))
    loop = asyncio.get_event_loop()
    try:
        print("Starting loop...")
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    mem.close()
    loop.close()


if __name__ == "__main__":
    main()
