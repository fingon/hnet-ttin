#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: nosefails.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Wed Mar 26 18:49:35 2014 mstenber
# Last modified: Thu Mar 27 12:57:42 2014 mstenber
# Edit time:     40 min
#
"""

Look at a number of nosetests outputs, and identify tests that are:

[- ok (no failures; ignored, as not visible in default nosetests output)]

- flaky (sometimes work)

- incosistently broken (never work, different place)

- consistently broken (never work, same place)

The point of this tool is to parse _a set_ of nosetests runs outputs,
and identify especially broken tests, and where they fail. The flaky
tests are also listed for completeness.

"""

import collections
import re


LOG_LENGTH=1

# What do we really want from the output logs? system calls seem reasonable
#spam_line_re = re.compile('(^asyncio:|.*result: False)').match
spam_line_re = None
useful_line_re = re.compile('^cotest: DEBUG: async_system (.*)$').match
#useful_line_re = None

fail_re = re.compile('^FAIL: (\S+) \((\S+)\)').match
start_log_re = re.compile('^-+ >> begin captured logging << -+$').match
end_log_re = re.compile('^-+ >> end captured logging << -+$').match

class Case:
    def __init__(self):
        self.traces = []
    def flaky(self):
        return '' in self.traces
    def inconsistent(self):
        return not self.flaky() and len(collections.Counter(self.traces)) > 1
    def broken(self):
        return not self.flaky() and not self.inconsistent()

def parse_logs(*logs):
    cases = {}
    for log in logs:
        state = 0
        dq = collections.deque(maxlen=LOG_LENGTH)
        c = None
        for line in open(log):
            if state == 0:
                m = fail_re(line)
                if m is None:
                    continue
                n, c = m.groups()
                n = '%s.%s' % (c, n)
                if n not in cases:
                    cases[n] = Case()
                c = cases[n]
                state = 1
            if state == 1 and start_log_re(line) is not None:
                state = 2
            if state == 2:
                if end_log_re(line) is not None:
                    c.traces.append('\n'.join(dq))
                    state = 0
                    continue
                if spam_line_re and spam_line_re(line) is not None:
                    continue
                if useful_line_re:
                    m = useful_line_re(line)
                    if m is None:
                        continue
                    line = m.group(1)
                dq.append(line.rstrip())
    # Add 'successful' results to the end
    for case in cases.values():
        need = len(logs) - len(case.traces)
        if need > 0:
            l = [''] * need
            case.traces.extend(l)
    return cases

def print_cases(cases, call, st, st1=False):
    keys = list(sorted(cases.keys()))
    keys = list(filter(lambda x:getattr(cases[x], call)(), keys))
    if not keys:
        return
    print(call, len(keys))
    for k in keys:
        print('',k)
        if st:
            for t, c in collections.Counter(cases[k].traces).items():
                if st1:
                    print('', '', t)
                    break
                print('', '', c, t)
    print()

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('logfile',
                    nargs='+',
                    help='Log files to parse')
    args = ap.parse_args()
    cases = parse_logs(*args.logfile)
    print_cases(cases, 'flaky', True)
    print_cases(cases, 'inconsistent', True)
    print_cases(cases, 'broken', True, True)

