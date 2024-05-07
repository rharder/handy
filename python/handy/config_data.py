#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""
import logging
import traceback
import warnings
from collections import UserDict
from datetime import datetime
from os import PathLike
from pathlib import Path
from typing import Optional, Union, Any, Dict, List

import yaml

logger = logging.getLogger(__name__)


class ConfigData(UserDict):

    def __init__(self, filename: Union[str, bytes, PathLike] = None, from_text: str = None):
        super().__init__()
        # If config data is specified from raw text
        self.from_text: str = from_text

        # If config data is specified from a file
        self.config_file: Path = Path(filename) if filename else None
        self.last_read: Optional[datetime] = None
        self._has_been_read: bool = False
        if not self.from_text and (self.config_file is None or not self.config_file.exists()):
            logger.warning(f"{self.__class__.__name__} config file does not exist: {self.config_file}")
        else:
            self._ensure_loaded()

    def __getitem__(self, key: str) -> Any:
        """Returns the item at the given key/key path and throws a key error if the key is not found.
        The returning of a default value is handled by the function that calls this one."""

        self._ensure_loaded()
        parts = Path(key).parts
        data: Union[List, Dict] = self.data
        for part in parts[:-1]:
            if part == "/":
                continue
            data = data[part]

        # In the case that the data element is an array, then we expect to pull an integer index
        if isinstance(data, list):
            return data[int(parts[-1])]

        elif data is not None:
            return data[parts[-1]]

    def get_path(self, path: str, default: Optional[Any] = None) -> Any:
        """Given a path to a resource, this will traverse the path, which may or
        may not exist in the config file."""
        warnings.warn("get_path() will be removed in favor of get()", DeprecationWarning)
        return self.get(path, default)

    def file_contents(self) -> str:
        try:
            with open(self.config_file, "r") as f:
                return f.read()
        except Exception as ex:
            logger.warning(f"Unable to read config file {self.config_file}: {ex}")

    def _ensure_loaded(self):
        # In the event there is no file specified, then we just have an in-memory empty dictionary
        if self.config_file is None and self.from_text is None:
            return

        # Handle config from stream
        if self.from_text is not None and not self._has_been_read:
            data = yaml.safe_load(self.from_text)
            self.update(data)
            self.last_read = datetime.now()
            self._has_been_read = True

        # Else if there's a config file
        elif self.config_file is not None and self.config_file.exists():
            # We cache the config data, and there several reasons why we will re-attempt to load the data:
            # - No existing cache
            # - File has changed
            mtime = datetime.fromtimestamp(self.config_file.stat().st_mtime) \
                if self.config_file and self.config_file.exists() else None

            if not self._has_been_read or (self.last_read and mtime and self.last_read < mtime):
                try:
                    with open(self.config_file) as f:
                        data = yaml.safe_load(f)
                    self._has_been_read = True
                    self.update(data)
                    self.last_read = mtime

                except Exception as ex:
                    logger.warning(f"Error while reading config file: {type(ex)} {ex}")
