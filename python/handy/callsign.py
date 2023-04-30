#!/usr/bin/env python3
# encoding: utf-8
"""
callsign.py

Created by Robert Harder on 2015-10-08.
Copyright (c) 2015 Robert Harder. All rights reserved.
"""

import string
import sys

import requests

__author__ = "Robert Harder, K6RWH"


def main():
    for arg in sys.argv[1:]:
        print_record(arg)


def callsign(cs):
    try:
        URL = "http://callook.info/index.php"
        r = requests.get(URL, params={'callsign': cs, 'display': 'json'})
        json = r.json()
        return json
    except Exception as e:
        print("Error", cs, e, file=sys.stderr)
        return None


def print_record(cs):
    record = callsign(cs)
    if record is not None:
        if record['status'] == 'INVALID':
            print(cs.upper())
        else:
            name = record['name'].title()
            print("{:8s}{}".format(cs.upper(), name))


if __name__ == '__main__':
    main()