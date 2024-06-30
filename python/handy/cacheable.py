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
import pickle
import shelve
import uuid
from collections import UserDict, namedtuple, defaultdict
from datetime import datetime, timedelta
from os import PathLike
from typing import Optional, Union, Any, TypeVar, Iterator, Dict, overload, Literal

import nacl, nacl.pwhash, nacl.utils, nacl.secret, nacl.exceptions

__author__ = "Robert Harder"
logger = logging.getLogger(__name__)
CacheableItem = namedtuple("CacheableItem", "value createdAt expiration")

V = TypeVar("V")


class Cacheable(UserDict[str, V]):
    """

    """
    DEFAULT_EXPIRATION_VAL = timedelta(hours=1)
    NONEXPIRING = timedelta()  # A zero timeout means non-expiring
    KDF_OPS_LIMIT_LOW = 3
    KDF_MEM_LIMIT_LOW = 8192

    def __init__(self,
                 filename: Union[str, bytes, PathLike] = None,
                 default_expiration: timedelta = None,
                 prefix: str = None,
                 data_backing: Dict = None,
                 password: Any = None,
                 kdf_quality: Literal["high", "low"] = "low"
                 ):
        super().__init__()
        self.filename: Optional[str] = str(filename) if filename else None
        self.default_expiration: Optional[timedelta] = default_expiration \
            if default_expiration is not None else self.DEFAULT_EXPIRATION_VAL
        self.prefix: Optional[str] = prefix or ""
        if data_backing is not None:
            self.data = data_backing

        # Data backing is broken in data and meta elements
        if "data" not in self.data:
            self.data["data"] = {}
        if "meta" not in self.data:
            self.data["meta"] = {}

        # Key is the salt, then the password is the key
        self.kdf_hash: Dict[bytes, Dict[Any, bytes]] = defaultdict(dict)

        self.salt: Optional[bytes] = None
        self.kdf_quality: Literal["high", "low"] = kdf_quality
        self.__kdf = nacl.pwhash.argon2i.kdf
        self.__ops = self.KDF_OPS_LIMIT_LOW \
            if kdf_quality == "low" else nacl.pwhash.argon2i.OPSLIMIT_SENSITIVE
        self.__mem = self.KDF_MEM_LIMIT_LOW \
            if kdf_quality == "low" else nacl.pwhash.argon2i.MEMLIMIT_SENSITIVE
        self.salt = self.get_meta(
            key="__SALT__",
            default=nacl.utils.random(nacl.pwhash.argon2i.SALTBYTES),
            save_default=True)
        self.symmetric_key = self._prepare_password(password) if password is not None else None

    def _prepare_password(self, password: Any) -> bytes:
        if self.salt in self.kdf_hash and password in self.kdf_hash[self.salt]:
            return self.kdf_hash[self.salt][password][password]

        if isinstance(password, str):
            password_bytes = password.encode("utf-8")
        else:
            password_bytes = pickle.dumps(password)
        print(f"Preparing password '{password}' with salt '{self.salt}'... ", end="", flush=True)
        prepared_password = nacl.pwhash.argon2i.kdf(
            size=nacl.secret.SecretBox.KEY_SIZE,
            password=password_bytes,
            salt=self.salt,
            opslimit=self.__ops, memlimit=self.__mem)
        print("Done")
        self.kdf_hash[self.salt][password] = prepared_password
        return prepared_password

    def _keytransform(self, key: Any) -> str:
        return f"{self.prefix}.{key}" if self.prefix else str(key)

    def __iter__(self):
        # Step 1: Combine iters from in-memory and disk
        keys = set(self.data["data"].keys())
        if self.filename:
            with shelve.open(self.filename, writeback=True) as db:
                if "data" not in db:
                    db["data"] = {}
                keys.update(db["data"].keys())

        # Step 2: Filter out keys that don't have correct prefix
        # Example, if prefix=cars then start=cars. and keys will be things like cars.bronco
        start = f"{self.prefix}." if self.prefix else ""
        correct_prefix = filter(lambda _k: _k.startswith(start), keys)

        # Step 3: Strip the leading prefix/start string so keys are original value
        stripped_keys = iter(x[len(start):] for x in correct_prefix)

        # Step 4: We'll check for the key's existence without checking crypto
        final_keys = []
        for k in stripped_keys:
            try:
                _ = self[k]
            except nacl.exceptions.CryptoError as _:
                # It's in there, but we didn't specify the password - that's ok
                final_keys.append(k)
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
            del self.data["data"][_key]
        except KeyError:
            ...
        if self.filename:
            with shelve.open(self.filename, writeback=True) as db:
                if "data" not in db:
                    db["data"] = {}
                try:
                    del db["data"][key]
                except KeyError:
                    ...

    def __len__(self) -> int:
        return len(list(iter(self)))

    def __contains__(self, key: Any) -> bool:
        _key = self._keytransform(key)

        # Step 1: Retrieve value
        item: Optional[CacheableItem] = None
        if _key in self.data["data"]:
            return True
        elif self.filename:
            with shelve.open(self.filename) as db:
                if "data" not in db:
                    db["data"] = {}
                if _key in db["data"]:
                    item = db["data"][_key]
                    self.data["data"][_key] = item  # Save to in-memory as well
                    return True
        return False

    def set(self,
            key: Any,
            value: V,
            expiration: timedelta = None,
            password=None) -> "Cacheable":
        """"Sets a value in the cache and optionally overrides the timeout for this key only"""
        self.__setitem__(key=key,
                         value=value,
                         expiration=expiration,
                         password=password)
        return self

    def __setitem__(self,
                    key: Any,
                    value: V,
                    expiration: timedelta = None,
                    password=None,
                    ) -> None:
        # Step 1: Add the prefix
        _key = self._keytransform(key)

        # Step 2: Encrypt the value object
        if password or self.symmetric_key:
            _pickled_value = pickle.dumps(value)
            _encr_key = self._prepare_password(password) if password is not None else self.symmetric_key
            _encr_box = nacl.secret.SecretBox(_encr_key)
            value = _encr_box.encrypt(_pickled_value)  # Nonce automatically included

        item = CacheableItem(value,
                             datetime.now(),
                             expiration if expiration is not None else self.default_expiration)

        # Step 3: Save the item both in the in-memory 'data' field and the file cache
        self.data["data"][_key] = item
        if self.filename:
            with shelve.open(self.filename, writeback=True) as db:
                if "data" not in db:
                    db["data"] = {}
                db["data"][_key] = item

    def __get_cacheable_item(self, key: any) -> CacheableItem:
        """Returns the CachableItem corresponding to the given key or raises
        an KeyError exception if the item is not there.  This does not
        attempt to decrypt the item, if it's encrypted."""
        _key = self._keytransform(key)

        # Step 1: Retrieve value
        item: Optional[CacheableItem] = None
        if _key in self.data["data"]:
            item = self.data["data"][_key]
        elif self.filename:
            with shelve.open(self.filename) as db:
                if "data" not in db:
                    db["data"] = {}
                if _key in db["data"]:
                    item = db["data"][_key]
                    self.data["data"][_key] = item  # Save to in-memory as well

        # Step 2: If not there, do __missing__ or raise KeyError
        if item is None:
            if hasattr(self.__class__, "__missing__"):
                return self.__class__.__missing__(self, key)
            raise KeyError(key)

        # Step 4: Else check if it actually is expired
        if item.expiration != self.NONEXPIRING:
            age = datetime.now() - item.createdAt
            if age > (item.expiration or self.default_expiration):
                msg = f"Cache expired for {_key}"
                logger.debug(msg)
                del self.data["data"][_key]  # Delete from memory
                if self.filename:
                    with shelve.open(self.filename) as db:
                        if "data" not in db:
                            db["data"] = {}
                        del db["data"][_key]  # Delete from file cache
                raise KeyError(msg)
        return item

    def get(self, key: Any, default: Any = None, password=None) -> Optional[V]:
        """Gets the item with the given key, using the default password or the
        provided password. If the key is not there, then None or the default value
        is returned.  If the password is wrong, a CryptoError is raised."""
        try:
            item = self.__get_cacheable_item(key)
        except KeyError:
            return default

        # Decrypt and return non-expired value
        return_value = item.value
        if password or self.symmetric_key:
            _encr_key = self._prepare_password(password) if password is not None else self.symmetric_key
            _encr_box = nacl.secret.SecretBox(_encr_key)
            try:
                _decr_value = _encr_box.decrypt(return_value)
            except nacl.exceptions.CryptoError as ex:
                # No problem, just return the default
                return default
            else:
                _unpickled_value = pickle.loads(_decr_value)
                return _unpickled_value

        return return_value

    def __getitem__(self, key: Any) -> V:
        """Returns the item at the given key and raises a KeyError if expired - just as if the key was not found"""
        item = self.__get_cacheable_item(key)  # KeyError if not there

        # Decrypt and return non-expired value
        return_value = item.value
        if self.symmetric_key:
            _encr_key = self.symmetric_key
            _encr_box = nacl.secret.SecretBox(_encr_key)
            _decr_value = _encr_box.decrypt(return_value)
            _unpickled_value = pickle.loads(_decr_value)
            return _unpickled_value

        return return_value

    def get_meta(self, key: Any,
                 default: Any = None,
                 save_default: bool = None) -> Any:
        _key = f"__meta__.{self._keytransform(key)}"

        # Step 1: Retrieve value
        item: Optional[Any] = None
        if _key in self.data["meta"]:
            item = self.data["meta"][_key]
        elif self.filename:
            with shelve.open(self.filename, writeback=save_default) as db:
                if "meta" not in db:
                    db["meta"] = {}
                if _key in db["meta"]:
                    item = db["meta"][_key]
                    self.data["meta"][_key] = item  # Save to in-memory as well
                elif save_default:
                    # Do we want to in-line save the default value for next time
                    db["meta"][_key] = default
                    self.data["meta"][_key] = default

        # Step 2: If not there, do __missing__ or raise KeyError
        return item if item is not None else default

    def set_meta(self, key: Any, value: Any) -> None:
        _key = f"__meta__.{self._keytransform(key)}"
        self.data["meta"][_key] = value
        if self.filename:
            with shelve.open(self.filename, writeback=True) as db:
                if "meta" not in db:
                    db["meta"] = {}
                db["meta"][_key] = value

    def sub_cache(self,
                  prefix: str = None,
                  default_expiration: timedelta = None,
                  password: Any = None) -> "Cacheable":
        """
        Creates a Cacheable object based on the parent but will add the given prefix to the keys
        making a handy way to have one Cacheable object that many parts of an application can use.
        Sub caches of sub caches will maintain the prefix inheritance
        """
        prefix = prefix or str(uuid.uuid4())
        composite_prefix = f"{self.prefix}.{prefix}" if self.prefix else str(prefix)
        subcache = Cacheable(
            filename=self.filename,
            default_expiration=default_expiration \
                if default_expiration is not None else self.default_expiration,
            prefix=composite_prefix,
            password=password,
            data_backing=self.data,
            kdf_quality=self.kdf_quality)
        if password is None and self.symmetric_key is not None:
            subcache.symmetric_key = self.symmetric_key

        subcache.kdf_hash = self.kdf_hash  # Share the KDF cache
        print(f"Subcache {prefix} salt={subcache.salt}")
        return subcache
