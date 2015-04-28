#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: analyze_cotest_deltas.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2015 cisco Systems, Inc.
#
# Created:       Tue Apr 28 12:00:39 2015 mstenber
# Last modified: Tue Apr 28 12:39:41 2015 mstenber
# Edit time:     15 min
#
"""

This is an utility which takes nose+cotest log file, and outputs
simply how long each step took. Notably it does NOT keep track of
individual steps but rather stupidly just looks at the cotest
recursion depth, and assumes first message at deeper depth = start
there, and messages at lower depths = end of the lower ones..

"""

import datetime
import re

TIMESTAMP_FORMAT='%Y-%m-%d %H:%M:%S'

log_re = re.compile('''(?x)
^(?P<ts>\d+-\d+-\d+\s\d+:\d+:\d+,\d+)\s
cotest\s\[(?P<depth>\d+)\]\s
(?P<body>.*)
$''').match

def _cotest_timestamp_to_datetime(s):
    assert ',' in s
    base, milli = s.split(',')
    dt = datetime.datetime.strptime(base, TIMESTAMP_FORMAT)
    milli = int(milli)
    if milli:
        dt = dt + datetime.timedelta(milliseconds=int(milli))
    return dt

def parse_cotest_log(f):
    stack = []
    def _pop_stack():
        (dt2, body) = stack.pop()
        print len(stack), dt, dt - dt2, body
    for line in f:
        m = log_re(line)
        if m is None: continue
        gr = m.groupdict()
        d = int(gr['depth'])
        dt = _cotest_timestamp_to_datetime(gr['ts'])
        assert d <= len(stack), 'got too deep stack: %d >> %d' % (d, len(stack))
        if d == len(stack):
            # Push new one
            stack.append((dt, gr['body']))
        elif d == len(stack) - 1:
            pass
        else:
            while d < (len(stack) - 1):
                _pop_stack()
    while stack:
        _pop_stack()

if __name__ == '__main__':
    import sys
    parse_cotest_log(sys.stdin)


