#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This class manages the reading of the config YAML file and has some helper methods for working with such a file.

If backed by a config file, the config file is "live" in the sense that as the Python code is running, if the
config file changes, those changes will be immediately reflected when a key is read from the config data.
This is done by observing the modification date on the file on the local filesystem and reloading the data
whenever the modification date is newer than the last time it was read.

If a config file is not provided as a backing, this class will still function by returning no values for whatever
keys are asked of it.
"""
import logging
import warnings
from collections import UserDict
from datetime import datetime
from os import PathLike
from pathlib import Path, PurePosixPath
from typing import Optional, Union, Any, Dict, List

import yaml
from colorama import Fore, Style

_BLUE = Fore.BLUE
_GREEN = Fore.GREEN
_RESET = Style.RESET_ALL

__author__ = "Robert Harder"
__email__ = "rharder@mitre.org"

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
        self.runtime_overrides: Dict[str, Any] = {}
        if self.config_file is not None and not self.config_file.exists():
            logger.warning(f"{self.__class__.__name__} config file does not exist: {self.config_file}")
        else:
            self._ensure_loaded()

    def __getitem__(self, key: str) -> Any:
        """Returns the item at the given key/key path and throws a key error if the key is not found.
        The returning of a default value is handled by the function that calls this one."""
        if key in self.runtime_overrides:
            return self.runtime_overrides[key]

        self._ensure_loaded()
        parts = PurePosixPath(key).parts
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

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def set_runtime_override(self, key: str, value: Any) -> None:
        self.runtime_overrides[key] = value

    @property
    def base_directory(self) -> Path:
        if self.config_file:
            path = self.config_file.parent.resolve()
        else:
            path = Path()
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        return path

    def get_filename_relative_to_config_file(self, key: str, make_parents: bool = None) -> Optional[Path]:
        """Looks up a key in the config and if it can be treated as a filename,
        returns the filename relative to the config file. Else returns None."""
        val = self.get(key)
        if val is None:
            return None

        path = (self.base_directory / val).resolve()

        if make_parents:
            path.parent.mkdir(parents=True, exist_ok=True)

        return path

    def get_directory_relative_to_config_file(self, key: str, make_parents: bool = None) -> Optional[Path]:
        """Looks up a key in the config and if it can be treated as a directory,
        returns the directory relative to the config file. Else returns None."""
        val = self.get(key)
        if not val:
            return None

        path = (self.base_directory / val).resolve()

        if make_parents:
            path.mkdir(parents=True, exist_ok=True)

        return path

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
