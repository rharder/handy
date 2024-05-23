#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A file-cacheable Dict-like structure using Python's shelve.
Supports expiration of cached entries down to the per-key level.
Supports creating sub-cache objects that are part of the root file store.
Sub-caches are based on a key hieararchy that creates compounds strings
(since all cache items need a flat key/value structure for Python's shelve).

All keys will be converted to strings.
"""
import logging
import shelve
import uuid
from collections import UserDict, namedtuple
from datetime import datetime, timedelta
from os import PathLike
from typing import Optional, Union, Any, TypeVar, Iterator, Dict

__author__ = "Robert Harder"

logger = logging.getLogger(__name__)
CacheableItem = namedtuple("CacheableItem", "value createdAt expiration")

V = TypeVar("V")


class Cacheable(UserDict[str, V]):
    DEFAULT_EXPIRATION_VAL = timedelta(hours=1)
    NONEXPIRING = timedelta()  # A zero timeout means non-expiring

    def __init__(self,
                 filename: Union[str, bytes, PathLike] = None,
                 default_expiration: timedelta = None,
                 prefix: str = None,
                 data_backing: Dict = None):
        super().__init__()
        self.filename: Optional[str] = str(filename) if filename else None
        self.default_expiration: Optional[timedelta] = default_expiration \
            if default_expiration is not None else self.DEFAULT_EXPIRATION_VAL
        self.prefix: Optional[str] = prefix or ""
        if data_backing is not None:
            self.data = data_backing

    def _keytransform(self, key: Any) -> str:
        return f"{self.prefix}.{key}" if self.prefix else str(key)

    def __iter__(self):
        # Step 1: Combine iters from in-memory and disk
        keys = set(self.data.keys())
        if self.filename:
            with shelve.open(self.filename) as db:
                keys.update(db.keys())

        # Step 2: Filter out keys that don't have correct prefix
        # Example, if prefix=cars then start=cars. and keys will be things like cars.bronco
        start = f"{self.prefix}." if self.prefix else ""
        correct_prefix = filter(lambda _k: _k.startswith(start), keys)

        # Step 3: Strip the leading prefix/start string so keys are original value
        stripped_keys = iter(x[len(start):] for x in correct_prefix)

        # Step 4: By trying to access the keys, we'll delete expired values
        final_keys = []
        for k in stripped_keys:
            try:
                _ = self[k]
            except KeyError:
                logger.warning(f"Removed expired key {k}")
            else:
                final_keys.append(k)

        return iter(final_keys)

    def __delitem__(self, key):
        # To avoid a race condition where we check that a key is present and then it expires right away,
        # we are just going to "try" to del from each location, and catch any exceptions.
        _key = self._keytransform(key)
        try:
            del self.data[_key]
        except KeyError:
            ...
        if self.filename:
            with shelve.open(self.filename) as db:
                try:
                    del db[key]
                except KeyError:
                    ...

    def __len__(self) -> int:
        return len(list(iter(self)))

    def __contains__(self, key: Any) -> bool:
        try:
            _ = self[key]
        except KeyError:
            return False
        else:
            return True

    def __getitem__(self, key: Any) -> V:
        """Returns the item at the given key and raises a KeyError if expired - just as if the key was not found"""
        _key = self._keytransform(key)

        # Step 1: Retrieve value
        item: Optional[CacheableItem] = None
        if _key in self.data:
            item = self.data[_key]
        elif self.filename:
            with shelve.open(self.filename) as db:
                if _key in db:
                    item = db[_key]
                    self.data[_key] = item  # Save to in-memory as well

        # Step 2: If not there, do __missing__ or raise KeyError
        if item is None:
            if hasattr(self.__class__, "__missing__"):
                return self.__class__.__missing__(self, key)
            raise KeyError(key)

        # Step 3: If item is non-expiring, just return it
        if item.expiration == self.NONEXPIRING:
            return item.value

        # Step 4: Else check if it actually is expired
        age = datetime.now() - item.createdAt
        if age > (item.expiration or self.default_expiration):
            msg = f"Cache expired for {_key}"
            logger.debug(msg)
            del self.data[_key]  # Delete from memory
            if self.filename:
                with shelve.open(self.filename) as db:
                    del db[_key]  # Delete from file cache
            raise KeyError(msg)

        else:
            # Return non-expired value
            return item.value

    def __setitem__(self, key: Any, value: Union[CacheableItem, V]) -> None:
        # Step 1: Add the prefix
        _key = self._keytransform(key)

        # Step 2: If this was a direct assignment, cache["foo"] = "bar", then we need to intercept and add expiration
        if not isinstance(value, CacheableItem):
            value = CacheableItem(value, datetime.now(), self.default_expiration)

        # Step 3: Save the item both in the in-memory 'data' field and the file cache
        self.data[_key] = value
        if self.filename:
            with shelve.open(self.filename) as db:
                db[_key] = value

    def set(self, key: Any, value: V, expiration: timedelta = None) -> None:
        """"Sets a value in the cache and optionally overrides the timeout for this key only"""
        self[key] = CacheableItem(value,
                                  datetime.now(),
                                  expiration if expiration is not None else self.default_expiration)

    def sub_cache(self, prefix: str = None, default_expiration: timedelta = None) -> "Cacheable":
        """
        Creates a Cacheable object based on the parent but will add the given prefix to the keys
        making a handy way to have one Cacheable object that many parts of an application can use.
        Sub caches of sub caches will maintain the prefix inheritance
        """
        prefix = prefix or str(uuid.uuid4())
        composite_prefix = f"{self.prefix}.{prefix}" if self.prefix else str(prefix)
        return Cacheable(
            filename=self.filename,
            default_expiration=default_expiration \
                if default_expiration is not None else self.default_expiration,
            prefix=composite_prefix,
            data_backing=self.data)
