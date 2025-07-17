#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import sys
import time
import uuid
from datetime import timedelta
from pathlib import Path
from unittest import TestCase

from mitrecollect.cacheable import Cacheable


# logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)


class TestCacheable(TestCase):

    def test_cacheable(self):
        filename = "deleteme-cacheable-test.sqlite3"

        # Test with file cache
        cache = Cacheable(filename, default_expiration=timedelta(milliseconds=100))

        # Test default expire
        cache.set("a", "alpha")
        self.assertEqual(cache.get("a"), "alpha")
        time.sleep(0.150)
        with self.assertRaises(KeyError):
            _ = cache["a"]
        self.assertIsNone(cache.get("a"))

        # Test override expire
        cache.set("b", "bravo", expiration=timedelta(seconds=1))
        self.assertEqual(cache.get("b"), "bravo")
        time.sleep(0.150)
        self.assertEqual(cache.get("b"), "bravo")
        time.sleep(1)
        self.assertIsNone(cache.get("b"))

        # Test default return
        cache.set("c", "charlie")
        self.assertEqual(cache.get("c"), "charlie")
        self.assertIsNone(cache.get("d"))
        self.assertEqual("foo", cache.get("d", "foo"))

        # Test non-expiring
        cache.set("nonexp", "nonexpring", expiration=cache.NON_EXPIRING)
        time.sleep(2)
        self.assertEqual(cache.get("nonexp"), "nonexpring")

    def test_key_iteration(self):
        cache = Cacheable()
        cache["a"] = "alpha"
        cache["b"] = "bravo"
        cache["c"] = "charlie"
        self.assertEqual({"a", "b", "c"}, set(cache.keys()))

        cache2 = Cacheable(password="monkey123")
        cache2["a"] = "alpha"
        cache2["b"] = "bravo"
        cache2["c"] = "charlie"
        # self.assertEqual({"a", "b", "c"}, set(cache2.keys()))

    def test_immediate_expire(self):
        cache = Cacheable(default_expiration=timedelta(milliseconds=100))
        # Test immediately-expiring
        cache.set("immediate-expire", "poof", expiration=cache.IMMEDIATE_EXPIRING)
        # print(cache.data)
        self.assertNotIn("immediate-expire", cache)

    def test_sub_cacheable(self):
        filename = f"deleteme-cacheable-test_test_sub_cacheable-{uuid.uuid4()}.sqlite3"

        cache = Cacheable(filename)
        cache.set("a", "a at level 1")
        self.assertEqual("a at level 1", cache.get("a"))

        # Create sub cache
        cache_animals = cache.sub_cache(prefix="animals")
        cache_animals.set("a", "alligator")
        self.assertEqual("alligator", cache_animals.get("a"))  # Sub cache
        self.assertEqual("a at level 1", cache.get("a"))  # Original cache

        # Create second sub cache
        cache_cars = cache.sub_cache(prefix="cars")
        cache_cars.set("a", "Alpha Romeo")
        cache_cars.set("b", "Bronco")
        self.assertEqual("Alpha Romeo", cache_cars.get("a"))  # Sub cache
        self.assertEqual("Bronco", cache_cars.get("b"))  # Sub cache
        self.assertEqual("a at level 1", cache.get("a"))  # Original cache

        # Create sub-sub cache of animals
        cache_animals_mammals = cache_animals.sub_cache(prefix="mammals")
        cache_animals_mammals.set("a", "aardvark")
        self.assertEqual("aardvark", cache_animals_mammals.get("a"))  # Sub sub cache
        self.assertEqual("alligator", cache_animals.get("a"))  # Sub cache
        self.assertEqual("a at level 1", cache.get("a"))  # Original cache

        # Now we're going to re-open the cache and check data
        del cache
        cache2 = Cacheable(filename)
        self.assertEqual("a at level 1", cache2.get("a"))
        self.assertGreater(len(cache2), 0)
        # Add animals
        cache2_animals = cache2.sub_cache(prefix="animals")
        self.assertEqual("alligator", cache2_animals.get("a"))  # Sub cache
        self.assertEqual("a at level 1", cache2.get("a"))  # Original cache

        # Add mammals
        cache2_animals_mammals = cache2_animals.sub_cache(prefix="mammals")
        self.assertEqual(1, len(cache2_animals_mammals))  # 1 Mammal
        self.assertEqual(2, len(cache2_animals))  # But 2 animals
        self.assertEqual("aardvark", cache_animals_mammals.get("a"))  # Sub sub cache
        self.assertIn("a", cache2_animals)

        # Try cars
        cache2_cars = cache2.sub_cache(prefix="cars")
        self.assertEqual(2, len(cache2_cars))
        self.assertIn("a", cache2_cars)
        self.assertIn("b", cache2_cars)
        self.assertEqual("Alpha Romeo", cache2_cars.get("a"))  # Sub cache
        self.assertEqual("Bronco", cache2_cars.get("b"))  # Sub cache
        self.assertEqual("Alpha Romeo", cache2_cars["a"])  # Sub cache
        self.assertEqual("Bronco", cache2_cars["b"])  # Sub cache

        count = 0
        for k in cache2_cars:
            self.assertIn(k, cache2_cars)
            count += 1
        self.assertEqual(2, count)

    def test_iterable(self):
        cache = Cacheable(default_expiration=timedelta(milliseconds=100), )
        cache.set("a", "alpha")
        cache.set("b", "bravo")
        cache.set("c", "charlie", expiration=timedelta(seconds=1))

        # All should be here, non-expired
        keys = ["a", "b", "c"]
        self.assertEqual(sorted(keys), list(sorted(cache.keys())))
        for k in cache:
            self.assertIn(k, keys)
        self.assertEqual(3, len(list(cache)))

        # If we delay 150 milliseconds, we should only have charlie left
        time.sleep(0.150)
        keys = ["c"]
        for k in cache:
            self.assertIn(k, keys)
        self.assertEqual(1, len(list(cache)))
        x = list(cache.values())
        self.assertEqual(["charlie"], x)

    def test_bracket_assign(self):
        cache = Cacheable(default_expiration=timedelta(milliseconds=100), )
        cache["a"] = "alpha"
        self.assertEqual("alpha", cache["a"])

    def test_delete(self):
        cache = Cacheable()
        cache["a"] = "alpha"
        self.assertIn("a", cache)
        self.assertEqual("alpha", cache["a"])
        del cache["a"]
        self.assertNotIn("a", cache)

        db_path = Path("deleteme-cacheable-test.sqlite3")
        db_path.unlink(missing_ok=True)
        cache = Cacheable(db_path)
        cache["a"] = "alpha"
        self.assertIn("a", cache)
        self.assertEqual("alpha", cache["a"])
        del cache["a"]
        self.assertNotIn("a", cache, cache)
        cache2 = Cacheable(db_path)
        self.assertNotIn("a", cache2)

    def test_alternate_keys(self):
        cache = Cacheable(filename="deleteme-cacheable-test_alternate_keys.sqlite3")
        cache[1] = "one"
        self.assertEqual("one", cache[1])  # Keys are converted to strings so this is OK
        self.assertEqual("one", cache["1"])  # Keys are converted to strings so this is OK

        cache2 = Cacheable(filename="deleteme-cacheable-test_alternate_keys.sqlite3")
        self.assertEqual(["1"], list(cache2))  # It's a string once it's been saved to disk

    def test_length(self):
        cache = Cacheable("deleteme-cacheable-test.sqlite3")
        cache["a"] = "alpha"  # Save at least one value

        cache2 = Cacheable("deleteme-cacheable-test.sqlite3")
        self.assertEqual(2, len(cache2.data))  # In-memory has two
        self.assertGreater(len(cache2), 0)  # But from disk we have something

        length = len(cache2)  # But we'll load from disk
        cache2[uuid.uuid4()] = "anything"
        self.assertEqual(length + 1, len(cache2))

    def test_values(self):
        cache = Cacheable()
        cache["a"] = "alpha"
        cache["b"] = "bravo"
        self.assertEqual(2, len(cache))
        self.assertEqual(2, len(cache.values()))
        for v in cache.values():
            self.assertIn(v, ["alpha", "bravo"])

    def test_access_sub_cache(self):
        # Test it behaves the same with and without a file-backing
        for filename in (None, "deleteme-cacheable-test.sqlite3"):
            cache = Cacheable(filename)
            sub = cache.sub_cache(prefix="sub")
            cache["mainlevel"] = "in the top level cache"
            sub["sublevel"] = "In the sub level cache"
            self.assertIn("mainlevel", cache)
            self.assertNotIn("mainlevel", sub)
            self.assertIn("sub.sublevel", cache)
            self.assertNotIn("sub.sublevel", sub)
            self.assertIn("sublevel", sub)

    def test_ttl(self):
        cache = Cacheable(default_expiration=timedelta(seconds=100), )
        cache["a"] = "alpha"
        self.assertAlmostEqual(timedelta(seconds=100).total_seconds(), cache.ttl("a").total_seconds(), delta=0.1)
        self.assertLess(cache.ttl("a"), timedelta(seconds=100))

        cache.set("b", "non-expring value goes here", cache.NON_EXPIRING)
        self.assertEqual(cache.ttl("b"), cache.NON_EXPIRING)

    def test_tic(self):
        cache = Cacheable(default_expiration=timedelta(seconds=100), )
        cache["a"] = "alpha"
        self.assertAlmostEqual(timedelta(seconds=100).total_seconds(), cache.ttl("a").total_seconds(), delta=0.1)
        self.assertLess(cache.ttl("a"), timedelta(seconds=100))

        time.sleep(2)
        self.assertAlmostEqual(timedelta(seconds=98).total_seconds(), cache.ttl("a").total_seconds(), delta=0.1)
        cache.tic("a")
        self.assertAlmostEqual(timedelta(seconds=100).total_seconds(), cache.ttl("a").total_seconds(), delta=0.1)

    def test_encryption(self):
        filename = "deleteme-cacheable-encryption-test.sqlite3"

        # An unencrypted cache will have the data cleartext inside it
        if os.path.exists(filename):
            os.remove(filename)
        special_key: bytes = f"myspecialkey-{uuid.uuid4()}".encode("utf-8")
        special_word: bytes = f"helloworld-{uuid.uuid4()}".encode("utf-8")
        cache_unencrypted = Cacheable(filename)
        cache_unencrypted[special_key] = special_word
        self.assertIn(special_key, cache_unencrypted)
        self.assertEqual(special_word, cache_unencrypted[special_key])
        with open(filename, "rb") as f:
            data = f.read()
        self.assertIn(special_key, data)
        self.assertIn(special_word, data)  # Data is visible in cleartext on the disk

        # An encrypted cache file will not have the key or data visible in cleartext
        if os.path.exists(filename):
            os.remove(filename)
        special_word: bytes = f"helloworld-{uuid.uuid4()}".encode("utf-8")
        special_key: bytes = f"myspecialkey-{uuid.uuid4()}".encode("utf-8")
        cache_encrypted = Cacheable(filename, password="monkey123")
        cache_encrypted[special_key] = special_word
        self.assertIn(special_key, cache_encrypted)
        self.assertEqual(special_word, cache_encrypted[special_key])
        with open(filename, "rb") as f:
            data = f.read()
        self.assertNotIn(special_key, data)  # Key is NOT visible in cleartext on the disk
        self.assertNotIn(special_word, data)  # Data is NOT visible in cleartext on the disk

        # Open the encrypted cache a second time
        cache2_encrypted = Cacheable(filename, password="monkey123")
        self.assertEqual(special_word, cache2_encrypted[special_key])

        # Open the encrypted cache with no password
        cache_no_password = Cacheable(filename)
        self.assertNotIn(special_key, cache_no_password)

        # Open the encrypted cache with the wrong password
        cache_wrong_password = Cacheable(filename, password="wrong-password")
        self.assertNotIn(special_key, cache_wrong_password)

        # Subcache also protected
        sub_cache_encr = cache_encrypted.sub_cache(prefix="lunch")
        sub_cache_encr["monday"] = "tacos"
        self.assertEqual("tacos", sub_cache_encr["monday"])
        with open(filename, "rb") as f:
            data = f.read()
        self.assertNotIn(b"monday", data)  # Key encrypted
        self.assertNotIn(b"tacos", data)  # Data encrypted
        # self.assertNotIn(b"lunch", data)  # Sub-cache name encrypted

        # Encrypted cache, still can iterate keys
        cache3 = Cacheable(filename, password="monkey123")
        self.assertIn(special_key, cache3)
        print(cache3)
        print(list(cache3.keys()))

        # Try encrypting individual entry
        special_key_2: bytes = f"myspecialkey2-{uuid.uuid4()}".encode("utf-8")
        special_word_2: bytes = f"helloworld2-{uuid.uuid4()}".encode("utf-8")
        special_password = "mySpecialPassword"
        cache_unencrypted.set(key=special_key_2, value=special_word_2, password=special_password)

        # Key will not appear without a password
        self.assertNotIn(special_key_2, cache_unencrypted)

        # Magically appears if we supply password
        self.assertEqual(special_word_2, cache_unencrypted.get(key=special_key_2, password=special_password))
