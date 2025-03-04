#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper functions for dates
"""

import logging
import math
import warnings
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional, Union

import dateutil.parser  # Pip install python-dateutil
import pytimeparse

__author__ = "Robert Harder"
__email__ = "rob@iHarder.net"

logger = logging.getLogger(__name__)


def example():
    print("human duration:", human_duration(timedelta(hours=4, minutes=10)))
    print("Now:", date_to_z(utcnow()))
    print("Relative time:", relative_time(utcnow() - timedelta(minutes=5, seconds=30)))


def date_to_z(dt: datetime, seconds_fractional_places: int = None) -> str:
    """Converts datetime to string format like 2023-08-04T18:35:12.697487Z.
     Accounts for any timezone.
     Assumes UTC if no timezone is embedded in the datetime object."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # Assume UTC
    elif dt.tzinfo != timezone.utc:
        dt = dt.astimezone(tz=timezone.utc)  # Shift to UTC
    if seconds_fractional_places is None:
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    else:
        micro_string = dt.strftime("%f")[:seconds_fractional_places]
        return dt.strftime(f"%Y-%m-%dT%H:%M:%S.{micro_string}Z")


def parse_date(date_string: Union[str, datetime], assume_utc: bool = True) -> datetime:
    """Parses complex dates including iso 8601 dates. Uses python-dateutil package.
    Will include timezone information if that is in the input, such as a Z suffix
    on 8601 times.  Will be timezone 'aware'."""
    try:
        if isinstance(date_string, datetime):
            d = date_string
        else:
            d = dateutil.parser.parse(date_string)
    except Exception as ex:
        # logger.warning(f"Error parsing date: {ex} (date_string={date_string})")
        ...
    else:
        if d.tzinfo is None:
            return ensure_timezone(d, tz=timezone.utc if assume_utc else None)
        else:
            return d


def ensure_utc(d: datetime) -> datetime:
    """Attaches UTC timezone to datetime if not already aware."""
    return ensure_timezone(d, tz=timezone.utc)


def ensure_timezone(d: datetime, tz: timezone = None) -> datetime:
    """Ensure datetime is timezone-aware, assumes local timezone if none given."""
    if d.tzinfo is None:
        if tz is None:
            d = d.astimezone()
        else:
            d = d.replace(tzinfo=tz)
    else:
        d = d.astimezone(tz)
    return d


def parse_duration(duration_string: str) -> timedelta:
    """Reads human-formatted strings like '5 min' and creates timedelta object."""
    try:
        sec = pytimeparse.parse(duration_string)
    except:
        ...
    else:
        return timedelta(seconds=sec) if sec else None


def utcnow() -> datetime:
    """Returns a timezone-aware datetime for UTC 'now'."""
    return datetime.utcnow().replace(tzinfo=timezone.utc)


def relative_time(at_time: datetime, relative_to: datetime = None) -> str:
    """Provides a relative string like '3 min ago' or '2 min from now'"""
    relative_to = relative_to or utcnow()

    if at_time < relative_to:  # Ago
        return f"{human_duration(relative_to - at_time)} ago"
    elif at_time > relative_to:  # From now
        return f"{human_duration(at_time - relative_to)} from now"
    else:
        return "now"


# def human_time(duration: timedelta):
#     warnings.warn(f"{__name__}.human_time() has been deprecated in favor of human_duration()",
#                   DeprecationWarning, 2)
#     return human_duration(duration)


def human_duration(duration: timedelta) -> Optional[str]:
    """Takes a timedelta and gives human-readable words like: 4 hours, 10 minutes"""
    # https://stackoverflow.com/questions/6574329/how-can-i-produce-a-human-readable-difference-when-subtracting-two-unix-timestam
    # if len(args) == 1 and isinstance(args[0], timedelta):
    #     secs = float(args[0].total_seconds())
    # else:
    #     secs = float(timedelta(*args, **kwargs).total_seconds())
    if duration is None:
        return None
    secs = duration.total_seconds()
    secs = int(secs)
    units = [("day", 86400), ("hour", 3600), ("minute", 60), ("second", 1)]
    parts = []
    for unit, mul in units:
        if secs / mul >= 1 or mul == 1:
            if mul > 1:
                n = int(math.floor(secs / mul))
                secs -= n * mul
                parts.append("%s %s%s" % (n, unit, "" if n == 1 else "s"))
            else:
                n = secs if secs != int(secs) else int(secs)
                if n > 0:
                    parts.append("%s %s%s" % (n, unit, "" if n == 1 else "s"))
    if not parts:
        parts.append("0 seconds")
    return ", ".join(parts)


def duration_8601(td: timedelta) -> str:
    """
    P is the duration designator (referred to as "period"), and is always placed at the beginning of the duration.
    Y is the year designator that follows the value for the number of years.
    M is the month designator that follows the value for the number of months.
    W is the week designator that follows the value for the number of weeks.
    D is the day designator that follows the value for the number of days.
    T is the time designator that precedes the time components.
    H is the hour designator that follows the value for the number of hours.
    M is the minute designator that follows the value for the number of minutes.
    S is the second designator that follows the value for the number of seconds.
    For example:
    P3Y6M4DT12H30M5S
    Source:
    https://www.digi.com/resources/documentation/digidocs/90001437-13/reference/r_iso_8601_duration_format.htm
    """
    dur = "P"
    if td.days:
        dur += f"{td.days}D"
    if td.seconds:
        dur += f"{td.seconds}S"
    return dur


@contextmanager
def timer(msg: str):
    """Simple with timer()... context for printing execution time for some code"""
    print(f"Timer Start: {msg} ...", flush=True)
    t1 = datetime.now()
    yield
    t2 = datetime.now()
    print(f"Timer End  : {msg} ... {human_duration(t2 - t1)}")


if __name__ == '__main__':
    example()
