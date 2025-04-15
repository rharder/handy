#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A file-cacheable Dict-like structure using sqlite for backend storage.
Supports expiration of cached entries down to the per-key level.
Supports creating sub-cache objects that are part of the root file store.
Sub-caches are based on a key hieararchy that creates compounds strings

All keys will be converted to strings.
"""
import logging
import pickle
import uuid
from collections import UserDict, defaultdict
from datetime import datetime, timedelta
from os import PathLike
from typing import Optional, Union, Any, TypeVar, Dict, Literal, Generic, List, Set, Iterable

import nacl
import nacl.exceptions
import nacl.pwhash
import nacl.secret
import nacl.utils
from sqlitedict import SqliteDict

__author__ = "Robert Harder"

logger = logging.getLogger(__name__)

V = TypeVar("V")


class CacheableItem(Generic[V]):
    def __init__(self, value: V = None, expiration: timedelta = None):
        self.value: V = value
        self.created_at: datetime = datetime.now()
        self.last_tic: datetime = self.created_at
        self.expiration: timedelta = expiration
        self.salt: bytes = nacl.utils.random(nacl.pwhash.argon2i.SALTBYTES)

    def __repr__(self):
        return (f"CacheableItem({self.value!r}, {self.created_at!r}, "
                f"{self.last_tic!r}, {self.expiration!r}, {self.salt.hex()!r})")

    @property
    def age_created_at(self) -> timedelta:
        return datetime.now() - self.created_at

    @property
    def age_last_tic(self) -> timedelta:
        return datetime.now() - self.last_tic

    @property
    def expired(self) -> bool:
        try:
            if self.expiration == Cacheable.NON_EXPIRING:
                return False
            else:
                if self.age_last_tic > self.expiration:
                    # logger.debug(f"Cacheable item expired, age={self.age_last_tic}")
                    # raise Exception("DELETE THIS RAISE LATER _ JUST LOOKING FOR TRACE")
                    return True
                # return self.age_last_tic > self.expiration
        except AttributeError:
            return True

    @property
    def expiration_date(self) -> datetime:
        return self.last_tic + self.expiration

    @property
    def ttl(self) -> timedelta:
        return self.expiration_date - datetime.now()

    def tic(self):
        """Updates the 'tic' datetime to now() thereby resetting the expiration date to now() + expiration."""
        self.last_tic = datetime.now()


class Cacheable(UserDict[str, V]):
    """

    """
    DEFAULT_EXPIRATION_VAL = timedelta(hours=1)
    NON_EXPIRING = timedelta()  # A zero timeout means non-expiring
    IMMEDIATE_EXPIRING = timedelta(seconds=-1)  # A negative value implies immediate expiration
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
                 parent: "Cacheable" = None,
                 ):
        super().__init__()
        self.parent: Cacheable = parent
        self._filename: Optional[str] = str(filename) if filename else None
        self.default_expiration: Optional[timedelta] = default_expiration \
            if default_expiration is not None else self.DEFAULT_EXPIRATION_VAL
        self.prefix: Optional[str] = prefix
        if data_backing is not None:  # I don't remember what I thought this data_backing thing is
            self.data = data_backing

        # Data backing is broken in data and meta elements (?)
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

        self.__cache_level_key: Optional[bytes] = None
        self.__salt: bytes = self.get_meta(
            key="__SALT__",
            default=nacl.utils.random(nacl.pwhash.argon2i.SALTBYTES),
            save_default=True)  # if password is not None else None
        # If a default password was provided, don't store it in memory - instead store the key
        self.__cache_level_key = self.hash_with_salt(password, self.__salt) \
            if password is not None else None

    def __str__(self):
        return (f"Cacheable(filename={self.filename!r}, "
                f"prefix={self.prefix!r}, "
                f"default_expiration={self.default_expiration!r},"
                f"password={'<REDACTED>' if self.__cache_level_key else 'NOT SET'})")

    @property
    def filename(self) -> str:
        if self._filename:
            return self._filename
        elif self.parent:
            return self.parent.filename

    @filename.setter
    def filename(self, filename: Union[str, bytes, PathLike]):

        # Step 1: if we're changing filenames, read the whole thing into memory
        if self._filename and self._filename != filename:
            try:
                with SqliteDict(self._filename, tablename=self.data_tablename) as db:
                    self.data.update(db)
                    logger.debug(f"Changing filenames, reading all data from old file {self._filename!r}")
            except Exception as ex:
                logger.warning(f"Could not read previous data when changing "
                               f"filenames from {self._filename!r} to {filename!r}: {ex}")

        # Step 2: Save the new filename
        self._filename = str(filename)

        # Step 3: Write everything to disk
        with SqliteDict(self.filename, tablename=self.data_tablename) as db:
            db.update(self.data)

    @property
    def data_tablename(self):
        # return f"data-{self._prefixtransform(self.prefix)}"
        return f"data-{self.prefix}"

    @property
    def meta_tablename(self):
        # return f"meta-{self._prefixtransform(self.prefix)}"
        return f"meta-{self.prefix}"

    def hash_with_salt(self, value: Any, salt: bytes) -> bytes:
        """Hash a value with the salt and returns the hashed value.

        Save the result in a cache so subsequent lookups are instant."""
        if salt in self.__kdf_hash_cache and value in self.__kdf_hash_cache[salt]:
            key = self.__kdf_hash_cache[salt][value]
            # print(f"Using cached key {self.hex(key)} for salt={self.hex(salt)}, password={self.hex(password)}")
            return key

        # Convert password to bytes
        if isinstance(value, str):
            password_bytes = value.encode("utf-8")
        elif isinstance(value, bytes):
            password_bytes = value
        else:
            password_bytes = pickle.dumps(value)

        # Run the KDF function, could take a while
        # print(f"Mixing '{self.hex(password)}' with salt '{self.hex(salt)}...' ", end="", flush=True)
        prepared_password = nacl.pwhash.argon2i.kdf(
            size=nacl.secret.SecretBox.KEY_SIZE,
            password=password_bytes,
            salt=salt,
            opslimit=self.ops_limit, memlimit=self.mem_limit)
        # print(f"Done: {self.hex(prepared_password)}")
        self.__kdf_hash_cache[salt][value] = prepared_password
        return prepared_password

    @staticmethod
    def hex(value: Any, length: int = 8) -> str:
        if isinstance(value, bytes):
            return value.hex()[:length]
        else:
            return str(value)[:length]

    def _keytransform(self, key: Any, password: Any = None) -> str:
        """Takes a key for the cache and prepares it by setting up namespace for subcaches and converting to string."""
        return_value = f"{self.prefix}.{key}" if self.prefix else str(key)

        # If the cache or the key is also protected, we need to encrypt/decrypt the key
        # But in the constructor, when the __SALT__ value is being retrieved, we don't
        if password is not None or self.__cache_level_key is not None:
            # 1: Cache-level key
            # 2: Mix with per-item password if there is one
            _encr_key = self.__cache_level_key if self.__cache_level_key is not None else self.__salt
            _encr_key = self.hash_with_salt(password, _encr_key[:nacl.pwhash.argon2i.SALTBYTES]) \
                if password is not None else _encr_key

            # _pickled_val = pickle.dumps(return_value)
            # _encr_box = nacl.secret.SecretBox(_encr_key)
            # return_value = _encr_box.encrypt(_pickled_val).hex()

            # eb2 = nacl.secret.SecretBox(_encr_key)
            # rv2 = eb2.encrypt(_pickled_val).hex()
            # SecretBox has a nonce, so the resulting value is
            # always different, making it the wrong choice for keys
            # Except that I want to
            # print(f"{return_value}\n{rv2}\n")

            # print(f"{key} ->({password}/{self.__cache_level_key}) {return_value}")

            _encr_value = self.hash_with_salt(return_value, _encr_key[:nacl.pwhash.argon2i.SALTBYTES])
            return_value = _encr_value.hex()

        return return_value

    def _prefixtransform(self, prefix: Any, password: Any = None) -> str:
        """Takes a key for the cache and prepares it by setting up namespace for subcaches and converting to string."""
        return_value = prefix or ""

        # If the cache or the key is also protected, we need to encrypt/decrypt the key
        # But in the constructor, when the __SALT__ value is being retrieved, we don't
        if password is not None or self.__cache_level_key is not None:
            # 1: Cache-level key
            # 2: Mix with per-item password if there is one
            _encr_key = self.__cache_level_key if self.__cache_level_key is not None else self.__salt
            _encr_key = self.hash_with_salt(password, _encr_key[:nacl.pwhash.argon2i.SALTBYTES]) \
                if password is not None else _encr_key
            # _pickled_val = pickle.dumps(return_value)
            # _encr_box = nacl.secret.SecretBox(_encr_key)
            # return_value = _encr_box.encrypt(_pickled_val).hex()
            _encr_value = self.hash_with_salt(return_value, _encr_key[:nacl.pwhash.argon2i.SALTBYTES])
            return_value = _encr_value.hex()

        return return_value

    # def _salt_and_hash(self, val: Any, password: Any = None)->bytes:
    #     # 1: Cache-level key
    #     # 2: Mix with per-item password if there is one
    #     _build_salt = self.__cache_level_key if self.__cache_level_key is not None else self.__salt
    #     _build_salt = self.hash_with_salt(password, _build_salt[:nacl.pwhash.argon2i.SALTBYTES]) \
    #         if password is not None else _build_salt
    #     return self.hash_with_salt(val, _build_salt[:nacl.pwhash.argon2i.SALTBYTES])

    def __collect_keys(self) -> Set[Any]:
        keys = set(self.data["data"].keys())
        # logger.debug(f"Found {len(keys):,} keys in self.data[]")
        if self.filename:
            with SqliteDict(self.filename, tablename=self.data_tablename) as db:
                keys.update(db.keys())
        # logger.debug(f"Found {len(keys):,} keys in self.data[] and {self.filename}")

        # Step 2: Filter out keys that don't have correct prefix
        # Example, if prefix=cars then start=cars. and keys will be things like cars.bronco
        start = f"{self.prefix}." if self.prefix else ""
        correct_prefix = filter(lambda _k: _k.startswith(start), keys)

        # Step 3: Strip the leading prefix/start string so keys are original value
        keys = iter(x[len(start):] for x in correct_prefix)

        return set(keys)

    def __iter__(self):
        keys = self.__collect_keys()
        #
        # # Step 1: Combine iters from in-memory and disk
        # keys = set(self.data["data"].keys())
        # if self.filename:
        #     with SqliteDict(self.filename, tablename=self.data_tablename) as db:
        #         keys.update(db.keys())
        #
        # # If encrypted, we need to decrypt the keys so we can read them
        # # keys = [self.decrypt_key(k) for k in keys]
        #
        # # Step 2: Filter out keys that don't have correct prefix
        # # Example, if prefix=cars then start=cars. and keys will be things like cars.bronco
        # start = f"{self.prefix}." if self.prefix else ""
        # correct_prefix = filter(lambda _k: _k.startswith(start), keys)
        #
        # # Step 3: Strip the leading prefix/start string so keys are original value
        # stripped_keys = iter(x[len(start):] for x in correct_prefix)

        # Step 4: We'll check for the key's existence without checking crypto
        final_keys = []
        for k in keys:
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
            with SqliteDict(self.filename, autocommit=True, tablename=self.data_tablename) as db:
                try:
                    del db[_key]
                    logger.debug(f"__delitem__: Deleted {_key} from sqlite file {self.filename}")
                except KeyError:
                    ...

    def __len__(self) -> int:
        return len(list(iter(self)))

    def __contains__(self, key: Any) -> bool:
        """Tests if key is stored and returns false if it's not or if it's expired."""
        _key = self._keytransform(key)

        # Step 1: Retrieve value
        item: Optional[CacheableItem] = None
        if "data" in self.data and _key in self.data["data"]:
            item = self.data["data"][_key]
            return not item.expired

        elif self.filename:
            with SqliteDict(self.filename, tablename=self.data_tablename) as db:
                if _key in db:
                    item = db[_key]
                    if item.expired:
                        return False
                    else:
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
        # self.__save(key=_key,item=item)
        if self.filename:
            with SqliteDict(self.filename, autocommit=True, tablename=self.data_tablename) as db:
                db[_key] = item

    def trim_expired(self) -> "Cacheable":
        """Trims expired keys and returns self (enabling chaining)"""
        keys = self.__collect_keys()
        # logger.debug(f"Examining {len(keys):,} keys to look for expired ones...")
        # Calling get_cacheable_items with all the keys (and not ignoring expiration)
        # is the same as bulk-deleting expired keys.
        items = self.get_cacheable_items(keys=keys, ignore_expiration=False)
        # logger.debug(f"Remaining non-expired items: {len(items):,}")
        return self

    def get_cacheable_item(self,
                           key: Any,
                           ignore_expiration: bool = None,
                           password: Any = None
                           ) -> Optional[CacheableItem]:
        """Returns the CachableItem corresponding to the given key
        This does not attempt to decrypt the item, if it's encrypted.
        Does not raise an exception - returns None if not present or expired.
        """
        _key = self._keytransform(key, password=password)

        # Step 1: Retrieve value
        item: Optional[CacheableItem] = None
        if _key in self.data["data"]:
            item = self.data["data"][_key]
        elif self.filename:
            with SqliteDict(self.filename, tablename=self.data_tablename) as db:
                if _key in db:
                    item = db[_key]
                    self.data["data"][_key] = item  # Cache to in-memory as well

        # Step 2: If not there, return None
        if item is None:
            return None

        # Step 4: Else check if it actually is expired
        if not ignore_expiration and item.expired:
            msg = f"Cache expired for {_key}"
            # logger.debug(msg)
            if "data" in self.data and _key in self.data["data"]:
                del self.data["data"][_key]  # Delete from memory
            if self.filename:
                with SqliteDict(self.filename, tablename=self.data_tablename, autocommit=True) as db:
                    if _key in db:
                        del db[_key]  # Delete from file cache
                        logger.debug(f"get_cacheable_item(): Deleted {_key} from sqlite file {self.filename}")
            return None

        return item

    def get_cacheable_items(self,
                            keys: Iterable[Any],
                            ignore_expiration: bool = None,
                            password: Any = None
                            ) -> Dict[Any, CacheableItem]:
        """Returns a group of CachableItems corresponding to the given keys
        This does not attempt to decrypt the item, if it's encrypted.
        Does not raise an exception - key will not be present in returned dictionary if not present or expired.
        """
        results: Dict[Any, CacheableItem] = {}

        _keys = [self._keytransform(k, password=password) for k in keys]

        # Step 1: Retrieve value from internal data first
        data_items = {k: self.data["data"][k] for k in _keys if k in self.data["data"]} if "data" in self.data else {}
        remaining_keys = [k for k in _keys if k not in data_items]
        db_items = {}
        if self.filename:
            with SqliteDict(self.filename, tablename=self.data_tablename) as db:
                db_items = {k: db[k] for k in remaining_keys if k in db}

        results.update(data_items)
        results.update(db_items)

        # Step 4: Else check if it actually is expired
        if not ignore_expiration:
            expired_keys = [k for k, v in results.items() if v.expired]
            if expired_keys:
                # Delete from memory
                for _key in expired_keys:
                    if "data" in self.data and _key in self.data["data"]:
                        del self.data["data"][_key]

                # Delete from database file (more efficient to do it in bulk)
                if self.filename:
                    with SqliteDict(self.filename, tablename=self.data_tablename, autocommit=True) as db:
                        for _key in expired_keys:
                            if _key in db:
                                del db[_key]  # Delete from file cache
                            else:
                                logger.warning(f"Tried to delete key={_key} but was not "
                                               f"found in database {self.filename}")
                # Remove from results
                for _key in expired_keys:
                    results.pop(_key)

                logger.debug(f"get_cacheable_items(): Bulk deleted {len(expired_keys):,} "
                             f"expired items from cacheable prefix={self.prefix}")

        return results

    def get(self, key: Any, default: Any = None, password=None) -> Optional[V]:
        """Gets the item with the given key, using the default password or the
        provided password. If the key is not there, then None or the default value
        is returned.
        @raise CryptoError: If the password is wrong.
        """
        item = self.get_cacheable_item(key, password=password)
        if item is None:
            # Not present or expired
            return default

        # Decrypt and return non-expired value
        return_value = item.value
        if password or self.__cache_level_key:
            try:
                # 1: Cache-level key (or salt alone if there was no cache-level password)
                # 2: Mix cache-level key with per-item salt
                # 3: Mix with per-item password if there is one
                _encr_key = self.__cache_level_key if self.__cache_level_key is not None else self.__salt
                _encr_key = self.hash_with_salt(_encr_key, item.salt)
                _encr_key = self.hash_with_salt(password, _encr_key[:nacl.pwhash.argon2i.SALTBYTES]) \
                    if password is not None else _encr_key
                _encr_box = nacl.secret.SecretBox(_encr_key)
                _decr_value = _encr_box.decrypt(return_value)
                _unpickled_value = pickle.loads(_decr_value)
                return _unpickled_value
            except nacl.exceptions.CryptoError as ex:
                logger.warning(f"Error decrypting key={key}: {type(ex).__name__}({ex})")
                return None

        return return_value

    def __getitem__(self, key: Any) -> V:
        """Returns the item at the given key and raises a KeyError if expired - just as if the key was not found.

        If a password is used for the cache, or the specific key, and the wrong password is provided,
        then a KeyError will also be raised as if the key does not exist.

        This protects from information leakage about what values are in
        the dictionary when the wrong password is provided.

        If you are using a per-key password, be sure to use the .get(key, password) function since
        using the bracket notation my_cache['myKey'] does not allow the password parameter to be supplied.
        @raises KeyError: If the key is not found or if it is expired or if the password is wrong.
        """
        item = self.get_cacheable_item(key)
        if item is None:
            if hasattr(self.__class__, "__missing__"):
                return self.__class__.__missing__(self, key)
            raise KeyError(key)

        # Decrypt and return non-expired value
        return_value = item.value
        if self.__cache_level_key:
            try:
                _encr_key = self.__cache_level_key
                _encr_key = self.hash_with_salt(_encr_key, item.salt)
                _encr_box = nacl.secret.SecretBox(_encr_key)
                _decr_value = _encr_box.decrypt(return_value)
                _unpickled_value = pickle.loads(_decr_value)
                return _unpickled_value
            except nacl.exceptions.CryptoError as ex:
                logger.warning(f"Error decrypting key={key}: {type(ex).__name__}({ex})")
                return None

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
            with SqliteDict(self.filename, tablename=self.meta_tablename, autocommit=True) as db:
                if _key in db:
                    item = db[_key]
                    self.data["meta"][_key] = item  # Save to in-memory as well
                elif save_default:
                    # Do we want to in-line save the default value for next time
                    db[_key] = default
                    self.data["meta"][_key] = default

        # Step 2: If not there, do __missing__ or raise KeyError
        return item if item is not None else default

    def set_meta(self, key: Any, value: Any) -> None:
        _key = f"__meta__.{self._keytransform(key)}"
        self.data["meta"][_key] = value
        if self.filename:
            with SqliteDict(self.filename, tablename=self.meta_tablename, autocommit=True) as db:
                db[_key] = value

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
            parent=self,
            # filename=self.filename,
            default_expiration=default_expiration \
                if default_expiration is not None else self.default_expiration,
            prefix=composite_prefix,
            password=password,
            data_backing=self.data,
            kdf_quality=self.kdf_quality,
        )
        if password is None and self.__cache_level_key is not None:
            subcache.__cache_level_key = self.__cache_level_key
        subcache.__kdf_hash_cache = self.__kdf_hash_cache  # Share the KDF cache
        return subcache

    def ttl(self, key: Any) -> timedelta:
        item = self.get_cacheable_item(key)
        if item:
            if item.expiration == Cacheable.NON_EXPIRING:
                return item.expiration
            else:
                return item.ttl

    def tic(self, key: Any):
        item = self.get_cacheable_item(key, ignore_expiration=True)
        if item:
            item.tic()
