#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from datetime import datetime
from pathlib import Path
from unittest import TestCase

from spaceutils.tle import TLE

from mitrecollect.config_data import ConfigData
from mitrecollect.messaging.legacy_messages import Portion, MU99, SU67, MultipleLines, MU15, GN00


class TestConfigData(TestCase):

    def test_path(self):
        """
        Looks like this:
LevelOne:
  foo: bar
  hello:
    - world
    - earth
    - universe
AnotherLevelOne:
  alpha:
    one: 1
    two: 2
    three: 3
  bravo:
    ten: 10
    twenty: 20
        """
        config = ConfigData("configtest.yml")
        self.assertEqual("bar", config["LevelOne/foo"])
        self.assertEqual("bar", config.get("LevelOne/foo"))
        with self.assertRaises(KeyError):
            _ = config["/Foobar"]

        # Lists
        self.assertEqual(["world", "earth", "universe"], config.get("LevelOne/hello"))
        self.assertEqual("world", config.get("LevelOne/hello/0"))
        with self.assertRaises(ValueError):
            config.get("/LevelOne/hello/foo")  # Should be an integer list index

        # Dictionaries
        self.assertEqual({"one": 1, "two": 2, "three": 3}, config.get("AnotherLevelOne/alpha"))
        self.assertEqual(1, config.get("AnotherLevelOne/alpha/one"))
        self.assertEqual(99, config.get("AnotherLevelOne/alpha/blah", 99))

        # test not exist, use default
        self.assertEqual("foo", config.get("I'mNotHere", "foo"))
