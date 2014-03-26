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
# Last modified: Wed Mar 26 19:23:29 2014 mstenber
# Edit time:     32 min
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
useful_line_re = re.compile('^.*sync_system').match
#useful_line_re = None

fail_re = re.compile('^FAIL: (\S+)').match
start_log_re = re.compile('^-+ >> begin captured logging << -+$').match
end_log_re = re.compile('^-+ >> end captured logging << -+$').match

class Case:
    def __init__(self):
        self.traces = ['']
    def flaky(self):
        return '' in self.traces
    def inconsistent(self):
        return not self.flaky() and len(collections.Counter(self.traces)) > 1
    def broken(self):
        return not self.flaky() and not self.inconsistent()

def parse_logs(*logs):
    cases = {}
    for log in logs:
        for case in cases.values():
            case.traces.append('')
        state = 0
        dq = collections.deque(maxlen=LOG_LENGTH)
        c = None
        for line in open(log):
            if state == 0:
                m = fail_re(line)
                if m is None:
                    continue
                n = m.group(1)
                if n not in cases:
                    cases[n] = Case()
                c = cases[n]
                state = 1
            if state == 1 and start_log_re(line) is not None:
                state = 2
            if state == 2:
                if end_log_re(line) is not None:
                    c.traces[-1] = '\n'.join(dq)
                    state = 0
                    continue
                if spam_line_re and spam_line_re(line) is not None:
                    continue
                if useful_line_re and useful_line_re(line) is None:
                    continue
                dq.append(line.rstrip())
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
                    print('',t)
                    break
                print(c,t)
    print()

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('logfile',
                    nargs='+',
                    help='Log files to parse')
    args = ap.parse_args()
    cases = parse_logs(*args.logfile)
    print_cases(cases, 'flaky', False)
    print_cases(cases, 'inconsistent', True)
    print_cases(cases, 'broken', True, True)

