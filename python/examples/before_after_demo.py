#!/usr/bin/env python3
"""
_Demo BeforeAndAfter class
"""

import sys

sys.path.append("..")  # because "examples" directory is sibling to the package
from handy.before_after import BeforeAndAfter

def main():
    demo_before_and_after()


def demo_before_and_after():
    import math
    print()
    print("::BeforeAndAfter with a timer")
    with BeforeAndAfter(before_msg="Begin... ", after_msg="Done: {:0.2f} sec"):
        for x in range(3000):
            math.factorial(x)

    print("::BeforeAndAfter without a timer")
    with BeforeAndAfter(before_msg="Begin... ", after_msg="Done."):
        for x in range(3000):
            math.factorial(x)

    print("::BeforeAndAfter with no messages")
    with BeforeAndAfter() as ba:
        for x in range(3000):
            math.factorial(x)
    print("Elapsed time:", ba.elapsed)

if __name__ == "__main__":
    main()
