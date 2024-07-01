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
from collections import UserDict, defaultdict
from datetime import datetime, timedelta
from os import PathLike
from typing import Optional, Union, Any, TypeVar, Dict, Literal, Generic

import nacl
import nacl.exceptions
import nacl.pwhash
import nacl.secret
import nacl.utils

__author__ = "Robert Harder"
logger = logging.getLogger(__name__)
# CacheableItem = namedtuple("CacheableItem", "value createdAt expiration")

V = TypeVar("V")


class CacheableItem(Generic[V]):
    def __init__(self, value: V = None, expiration: timedelta = None):
        self.value: V = value
        self.created_at: datetime = datetime.now()
        self.expiration: timedelta = expiration
        self.salt: bytes = nacl.utils.random(nacl.pwhash.argon2i.SALTBYTES)

    def __repr__(self):
        return f"CacheableItem({self.value!r}, {self.created_at!r}, {self.expiration!r}, {self.salt.hex()!r})"

    @property
    def age(self) -> timedelta:
        return datetime.now() - self.created_at

    @property
    def expired(self) -> bool:
        try:
            if self.expiration == Cacheable.NONEXPIRING:
                return False
            else:
                return self.age > self.expiration
        except AttributeError:
            return True


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
                 kdf_quality: Literal["high", "medium", "low"] = "low",
                 kdf_ops_limit: int = None,
                 kdf_mem_limit: int = None,
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
        # Manages for subcaches too (thus different salts)
        self.__kdf_hash_cache: Dict[bytes, Dict[Any, bytes]] = defaultdict(dict)
        self.kdf_quality: Literal["high", "medium", "low"] = kdf_quality
        self.ops_limit: int = nacl.pwhash.argon2i.OPSLIMIT_MIN  # Start with low
        self.mem_limit: int = nacl.pwhash.argon2i.MEMLIMIT_MIN
        if kdf_quality == "medium":
            self.ops_limit = nacl.pwhash.argon2i.OPSLIMIT_INTERACTIVE
            self.mem_limit = nacl.pwhash.argon2i.MEMLIMIT_INTERACTIVE
        elif kdf_quality == "high":
            self.ops_limit = nacl.pwhash.argon2i.OPSLIMIT_MODERATE
            self.mem_limit = nacl.pwhash.argon2i.MEMLIMIT_MODERATE
        if kdf_ops_limit is not None:
            self.ops_limit: int = kdf_ops_limit
        if kdf_mem_limit is not None:
            self.mem_limit: int = kdf_mem_limit

        self.__salt: bytes = self.get_meta(
            key="__SALT__",
            default=nacl.utils.random(nacl.pwhash.argon2i.SALTBYTES),
            save_default=True)
        # If a default password was provided, don't store it in memory - instead store the key
        self.__cache_level_key = self.hash_with_salt(password, self.__salt) if password is not None else None

    def hash_with_salt(self, password: Any, salt: bytes) -> bytes:
        """Hash a password with the salt and return the secret key.
        Save the result in a cache so subsequent lookups are instant."""
        if salt in self.__kdf_hash_cache and password in self.__kdf_hash_cache[salt]:
            key = self.__kdf_hash_cache[salt][password]
            print(f"Using cached key {self.hex(key)} for salt={self.hex(salt)}, password={self.hex(password)}")
            return key

        # Convert password to bytes
        if isinstance(password, str):
            password_bytes = password.encode("utf-8")
        elif isinstance(password, bytes):
            password_bytes = password
        else:
            password_bytes = pickle.dumps(password)

        # Run the KDF function, could take a while
        print(f"Mixing '{self.hex(password)}' with salt '{self.hex(salt)}...' ", end="", flush=True)
        prepared_password = nacl.pwhash.argon2i.kdf(
            size=nacl.secret.SecretBox.KEY_SIZE,
            password=password_bytes,
            salt=salt,
            opslimit=self.ops_limit, memlimit=self.mem_limit)
        print(f"Done: {self.hex(prepared_password)}")
        self.__kdf_hash_cache[salt][password] = prepared_password
        return prepared_password

    @staticmethod
    def hex(value: Any, length: int = 8) -> str:
        if isinstance(value, bytes):
            return value.hex()[:length]
        else:
            return str(value)[:length]

    def _keytransform(self, key: Any) -> str:
        """Takes a key for the cache and prepares it by setting up namespace for subcaches and converting to string."""
        return f"{self.prefix}.{key}" if self.prefix else str(key)

    def __iter__(self):
        # Step 1: Combine iters from in-memory and disk
        keys = set(self.data["data"].keys())
        if self.filename:
            with shelve.open(self.filename) as db:
                if "data" in db:
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
            item = self.get_cacheable_item(k)
            if item is not None:
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
                if "data" in db:
                    try:
                        del db["data"][_key]
                    except KeyError:
                        ...

    def __len__(self) -> int:
        return len(list(iter(self)))

    def __contains__(self, key: Any) -> bool:
        _key = self._keytransform(key)

        # Step 1: Retrieve value
        item: Optional[CacheableItem] = None
        if _key in self.data["data"]:
            return True  # Contains the key
        elif self.filename:
            with shelve.open(self.filename) as db:
                if "data" in db and _key in db["data"]:
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
                    password: Any = None,
                    ) -> None:
        # Step 1: Add the prefix
        _key = self._keytransform(key)

        item = CacheableItem(value=value,
                             expiration=expiration if expiration is not None else self.default_expiration)

        # Step 2: Encrypt the value object
        if password or self.__cache_level_key:
            _pickled_value = pickle.dumps(item.value)
            # 1: Cache-level key (or salt alone if there was no cache-level password)
            # 2: Mix cache-level key with per-item salt
            # 3: Mix with per-item password if there is one
            _encr_key = self.__cache_level_key if self.__cache_level_key is not None else self.__salt
            _encr_key = self.hash_with_salt(_encr_key, item.salt)
            _encr_key = self.hash_with_salt(password, _encr_key[:nacl.pwhash.argon2i.SALTBYTES]) \
                if password is not None else _encr_key
            _encr_box = nacl.secret.SecretBox(_encr_key)
            item.value = _encr_box.encrypt(_pickled_value)  # Nonce automatically included

        # Step 3: Save the item both in the in-memory 'data' field and the file cache
        self.data["data"][_key] = item
        if self.filename:
            with shelve.open(self.filename, writeback=True) as db:
                if "data" not in db:
                    db["data"] = {}
                db["data"][_key] = item

    def get_cacheable_item(self, key: any) -> Optional[CacheableItem]:
        """Returns the CachableItem corresponding to the given key
        This does not attempt to decrypt the item, if it's encrypted.
        Does not raise an exception - returns None if not present or expired.
        """
        _key = self._keytransform(key)

        # Step 1: Retrieve value
        item: Optional[CacheableItem] = None
        if _key in self.data["data"]:
            item = self.data["data"][_key]
        elif self.filename:
            with shelve.open(self.filename) as db:
                if "data" in db and _key in db["data"]:
                    item = db["data"][_key]
                    self.data["data"][_key] = item  # Cache to in-memory as well

        # Step 2: If not there, do __missing__ or raise KeyError
        if item is None:
            return None

        # Step 4: Else check if it actually is expired
        if item.expired:
            msg = f"Cache expired for {_key}"
            logger.debug(msg)
            if "data" in self.data and _key in self.data["data"]:
                del self.data["data"][_key]  # Delete from memory
            if self.filename:
                with shelve.open(self.filename, writeback=True) as db:
                    if "data" in db and _key in db["data"]:
                        del db["data"][_key]  # Delete from file cache
            return None
            # raise KeyError(msg)

        return item

    def get(self, key: Any, default: Any = None, password=None) -> Optional[V]:
        """Gets the item with the given key, using the default password or the
        provided password. If the key is not there, then None or the default value
        is returned.
        @raise CryptoError: If the password is wrong.
        """
        item = self.get_cacheable_item(key)
        if item is None:
            # Not present or expired
            return default

        # Decrypt and return non-expired value
        return_value = item.value
        if password or self.__cache_level_key:
            # 1: Cache-level key (or salt alone if there was no cache-level password)
            # 2: Mix cache-level key with per-item salt
            # 3: Mix with per-item password if there is one
            _encr_key = self.__cache_level_key if self.__cache_level_key is not None else self.__salt
            _encr_key = self.hash_with_salt(_encr_key, item.salt)
            _encr_key = self.hash_with_salt(password, _encr_key[:nacl.pwhash.argon2i.SALTBYTES]) \
                if password is not None else _encr_key

            # _encr_key = self.__key_from_password(password) if password is not None else self.__cache_level_key
            _encr_box = nacl.secret.SecretBox(_encr_key)
            _decr_value = _encr_box.decrypt(return_value)
            _unpickled_value = pickle.loads(_decr_value)
            return _unpickled_value

        return return_value

    def __getitem__(self, key: Any) -> V:
        """Returns the item at the given key and raises a KeyError if expired - just as if the key was not found
        If a password is used for the cache, but a specific password was used for the key, then this will
        raise a CryptoError when trying to decrypt with the wrong password. If you are using a per-item password,
        be sure to use the .get() function instead of cache["something"].

        @raises KeyError: If the key is not found or if it is expired
        @raises CryptoError: If the password is wrong.
        """
        item = self.get_cacheable_item(key)
        if item is None:
            if hasattr(self.__class__, "__missing__"):
                return self.__class__.__missing__(self, key)
            raise KeyError(key)

        # Decrypt and return non-expired value
        return_value = item.value
        if self.__cache_level_key:
            _encr_key = self.__cache_level_key
            _encr_key = self.hash_with_salt(_encr_key, item.salt)
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
        if password is None and self.__cache_level_key is not None:
            subcache.__cache_level_key = self.__cache_level_key
        subcache.__kdf_hash_cache = self.__kdf_hash_cache  # Share the KDF cache
        print(f"Subcache {prefix} salt={subcache.__salt}")
        return subcache
