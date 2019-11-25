#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helper class for collecting rates on how frequently something happens."""
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"


def main():
    fc = FrequencyCollector()
    topic = "foo"
    # topics = ["foo", "bar"]
    # for i in range(10):
    #     topic = random.choice(topics)
    #     fc.tic(topic, 2)
    #     time.sleep(1)
    #     # print(topic, i, fc.freq(topic), fc.freq(topic, hz_base=timedelta(seconds=60)))
    #     print(repr(fc))
    #
    # Test History Clearing
    for i in range(5):
        time.sleep(1)
        fc.tic(topic, i)
    print(fc._history)
    fc.max_history = timedelta(seconds=3)
    time.sleep(.1)
    fc._clear_old_history(topic)
    print(fc._history)


class FrequencyCollector:
    def __init__(self, hz_base: timedelta = None, history_base: timedelta = None, max_history: timedelta = None):
        self.hz_base: Optional[timedelta] = hz_base or timedelta(seconds=1)
        self.history_base: Optional[timedelta] = history_base
        self.max_history: Optional[timedelta] = max_history
        self._history: Dict[str, List[Tuple]] = dict()  # Tuples are (timestamp, count)
        self._listeners: Dict[str, List] = defaultdict(list)
        self._header_count_last_repr = 0

    def __repr__(self, include_header=False):
        headers = sorted(list(self._history.keys()))
        longest_header = max(6, *[len(h) for h in headers])
        resp = ""
        if include_header or len(headers) > self._header_count_last_repr:
            for h in headers:
                fmt = "{:>" + str(longest_header) + "s} "
                resp += fmt.format(h)
            else:
                resp += "\n"
        for h in headers:
            fmt = "{:>" + str(longest_header) + ".2f} "
            resp += fmt.format(self.freq(h))
        self._header_count_last_repr = len(headers)
        return resp

    def add_listener(self, topic, listener):
        self._listeners[topic].append(listener)

    def remove_listener(self, topic, listener):
        self._listeners[topic].remove(listener)

    def tic(self, topic: str, count=1):
        now = datetime.now()
        if topic not in self._history:
            self._history[topic] = list()
        self._history[topic].append((now, count))
        self._clear_old_history(topic)
        self._fire_change(topic)

    def freq(self, topic, hz_base: timedelta = None, history_base: timedelta = None) -> float:
        """Returns an average frequency for the topic.
        Can be adjusted for a different hz_base (default is "per second") and
        can be calculated over a given history_base (default is the whole history)"""
        now = datetime.now()
        hz_base: timedelta = hz_base or self.hz_base
        history_base: timedelta = history_base or self.history_base
        self._clear_old_history(topic)
        sum_of_samples = 0
        count_of_samples = 0
        oldest_dt: datetime = now
        cutoff_date = now - history_base if history_base else None
        for i in range(len(self._history.get(topic, [])), 0, -1):
            _rec = self._history[topic][i - 1]
            _dt: datetime = _rec[0]
            _n: int = _rec[1]
            if cutoff_date and _dt < cutoff_date:
                break
            sum_of_samples += _rec[1]
            count_of_samples += 1
            oldest_dt = _dt
        span: timedelta = now - oldest_dt
        try:
            freq = sum_of_samples / span.total_seconds() * hz_base.total_seconds()
        except ZeroDivisionError:
            return 0
        else:
            return freq
        finally:
            self._fire_change(topic)

    def freq_all(self, hz_base: timedelta = None, history_base: timedelta = None) -> Dict[str, float]:
        data = {}
        for topic in self._history.keys():
            data[topic] = self.freq(topic=topic, hz_base=hz_base, history_base=history_base)
        return data

    def topics(self) -> Tuple[str]:
        return tuple(self._history.keys())

    def _fire_change(self, topic: str):
        for listener in self._listeners[topic]:
            listener.topic_changed(topic, self)

    def _clear_old_history(self, topic):
        if self.max_history is None or topic not in self._history:
            return
        history = self._history[topic]
        now = datetime.now()
        while history and history[0][0] < now - self.max_history:
            history.pop(0)


if __name__ == '__main__':
    main()
