# -*- coding: utf-8 -*-
"""
For batching iterables
"""


def chunked(generator, size):
    """Read parts of the generator, pause each time after a chunk"""
    # https://stackoverflow.com/questions/8290397/how-to-split-an-iterable-in-constant-size-chunks
    # islice returns results until 'size',
    # make_chunk gets repeatedly called by iter(callable).
    from itertools import islice
    gen = iter(generator)
    make_chunk = lambda: list(islice(gen, size))
    return iter(make_chunk, [])