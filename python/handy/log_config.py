#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper class I use to assist in logging capabilities.
"""

import logging
import logging.handlers

import platform
import time
from os import PathLike

from typing import Union, Iterable

__author__ = "Robert Harder"

logger = logging.getLogger(__name__)


class LogFormat:
    info_log_format = "[%(levelname)-5.5s] %(message)s"
    verbose_log_format = "%(asctime)s [%(levelname)-5.5s] [%(name)-14.14s] %(message)s"

    @staticmethod
    def format_for(level: int):
        if level >= logging.INFO:
            return LogFormat.info_log_format
        else:
            return LogFormat.verbose_log_format


class LogFile:
    """For configuring options for logging to a file. Basic logging, no rotating files.
    Uses logging.FileHandler.
    """

    def __init__(self, level: int, filename: Union[str, bytes, PathLike]):
        self.level: int = level
        self.filename: Union[str, bytes, PathLike] = filename

    def handler(self) -> logging.FileHandler:
        h = logging.FileHandler(filename=self.filename)
        h.setLevel(self.level)
        h.setFormatter(logging.Formatter(LogFormat.format_for(self.level)))
        return h


class RotatingLogFile(LogFile):
    """For configuring options for logging to a file that rotates based on the size of the
    log file and number of backup log files to keep.
    Uses logging.handlers.RotatingFileHandler.
    """

    def __init__(self, level: int, filename: Union[str, bytes, PathLike], max_bytes: int, backup_count: int):
        super().__init__(level=level, filename=filename)
        self.max_bytes: int = max_bytes
        self.backup_count: int = backup_count

    def handler(self) -> logging.handlers.RotatingFileHandler:
        h = logging.handlers.RotatingFileHandler(
            filename=self.filename,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count)
        h.setLevel(self.level)
        h.setFormatter(logging.Formatter(LogFormat.format_for(self.level)))
        return h


class TimedRotatingLogFile(LogFile):
    """For configuring options for logging to a file that rotates based on time passing.
    Uses logging.handlers.TimedRotatingFileHandler.
    """

    def __init__(self, level: int, *kargs, **kwargs):
        """
        :param level: logging level
        :param kargs: parameters passed to TimedRotatingFileHandler
        :param kwargs: parameters passed to TimedRotatingFileHandler
        """
        super().__init__(level=level, filename=kwargs["filename"])
        self.kargs = kargs
        self.kwargs = kwargs

    def handler(self) -> logging.handlers.TimedRotatingFileHandler:
        h = logging.handlers.TimedRotatingFileHandler(*self.kargs, **self.kwargs)
        h.setLevel(self.level)
        h.setFormatter(logging.Formatter(LogFormat.format_for(self.level)))
        return h


def config(console_level: int = None,
           syslog_level: int = None,
           hush: Iterable = None,
           log_files: Iterable[LogFile] = None,
           other_handlers: Iterable[logging.Handler] = None
           ):
    """
    Config log stuff here.


    Example call:

    log_config.config(
        console_level=logging.INFO,
        hush=("urllib3", "file_dict", "chardet", "async_throttled_worker"),
        log_files=[
            log_config.TimedRotatingLogFile(level=logging.DEBUG,
                                            filename="logging-verbose.log",
                                            when="d", interval=1, backupCount=4),
            log_config.TimedRotatingLogFile(level=logging.INFO,
                                            filename="logging-info.log",
                                            when="d", interval=1, backupCount=10)
        ]
    )

    :param hush: List of logger names that should be suppressed down to WARNING levels
    """
    console_level = console_level or logging.INFO
    handlers = list()
    info_log_format = "[%(levelname)-5.5s] %(message)s"
    verbose_log_format = "%(asctime)s [%(levelname)-5.5s] [%(name)-14.14s] %(message)s"

    # Console
    if console_level:
        _fmt = info_log_format if console_level >= logging.INFO else verbose_log_format
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level=console_level)
        console_handler.setFormatter(logging.Formatter(_fmt))
        handlers.append(console_handler)
        del _fmt

    # Syslog for platforms that have it
    if syslog_level and platform.system() in ("Linux"):  # , "Darwin"):
        _fmt = info_log_format if console_level >= logging.INFO else verbose_log_format
        _address = "/dev/log"  # TODO: different platforms have different places this is supposed to go
        syslog_handler = logging.handlers.SysLogHandler()
        # facility=logging.handlers.SysLogHandler.LOG_DAEMON,
        # address=_address)
        syslog_handler.setLevel(syslog_level)
        syslog_handler.setFormatter(logging.Formatter(_fmt))
        handlers.append(syslog_handler)
        del _address, _fmt

    # Multiple log files are possible
    if log_files:
        for _lf in log_files:
            handlers.append(_lf.handler())

    # Other arbitrary handlers
    if other_handlers:
        handlers += other_handlers

    # I don't know why PyCharm complains about the following function call.
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=handlers
    )

    # For some packages, push logging level down to WARNING
    if hush:
        for _quieter in hush:
            logging.getLogger(_quieter).setLevel(logging.WARNING)


if __name__ == '__main__':
    config(
        console_level=logging.INFO,
        syslog_level=logging.INFO,
        hush=("urllib3", "file_dict", "chardet", "async_throttled_worker"),
        log_files=[
            LogFile(level=logging.DEBUG, filename="logtest-LogFile.log"),
            RotatingLogFile(level=logging.INFO,
                            filename="logtest-RotatingLogFile.log",
                            max_bytes=100,
                            backup_count=3),
            TimedRotatingLogFile(level=logging.INFO,
                                 filename="logtest-TimedRotatingLogFile.log",
                                 when="s",
                                 interval=3)
        ],
        other_handlers=[
            # logging.handlers.NTEventLogHandler("foobar"),
            # logging.handlers.SysLogHandler()
        ]
    )
    logger.info("Here's an INFO example")
    logger.error("Here's an ERROR example")
    logger.debug("Here's a DEBUG example")

    for i in range(20):
        logger.info(f"Log entry {i}")
        time.sleep(0.5)
