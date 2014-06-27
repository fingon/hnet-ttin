#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: stress2svg.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Wed Jun 11 12:57:29 2014 mstenber
# Last modified: Fri Jun 27 17:22:59 2014 mstenber
# Edit time:     66 min
#
"""

Produce SVG graph out of (historic) stress test results.

"""

import pygal
from pygal.style import Style
import nosefails

import argparse
import glob
import os
import re
import sys

def uniquify(l):
    # Remove shared substrings
    firsts = [x[0] for x in l]
    diff = [c for c in firsts if c != firsts[0]]
    if diff:
        return l
    # Can remove first character
    nexts = [x[1:] for x in l]
    return uniquify(nexts)

def startify(l):
    s = ''
    for e in l:
        if e[0] != s:
            s = e[0]
            yield e

ap = argparse.ArgumentParser()
ap.add_argument('directory',
                nargs='+',
                help='Log file directory to parse')
ap.add_argument('-c', '--cases', action='store_true')
args = ap.parse_args()

results = list(nosefails.parse_logs(*glob.glob('%s/log*.txt' % dir)) for dir in args.directory)

error_locations = [
    ('netkit start', '^(rm|.*echo foo|.*MConsoleDeadException)'),
#    ('IPv6 global', '^uml_mconsole .*ip -6 addr show.*200'),
    ('IPv6 address', '^uml_mconsole .*ip -6 addr'),
    ('IPv6 ping', '^.*ping6 .*h-server'),
    ('IPv6 ping (CPE)', '^.*ping6 .*(::192|2000:)'),
    ('IPv6 ping (DNS)', '^.*ping6 .*server.v6.lab.example.com'),
    ('IPv6 ping (SD)', '^.*ping6 .*(openwrt|cpe|ir[23]|bird)'),
    ('IPv6 PCP-MAP', '^.*pcp_map.py -6'),
    ('IPv6 MAPped', '^.*socat.*(tcp|udp)6:'),
    ('IPv4 address', '^uml_mconsole .*(ip -4 addr|ifconfig.*inet addr:)'),
    ('IPv4 ping', '^.*ping .*h-server'),
    ('IPv4 ping (DNS)', '^.*ping .*server.v4.lab.example.com'),
    ('IPv4 ping (SD)', '^.*ping .*(cpe|ir[23]|bird)'),
    ('IPv4 PCP-MAP', '^.*pcp_map.py -4'),
    ('IPv4 MAPped', '^.*socat.*(tcp|udp)4:'),
    ('tests ok, crashed', '.*ProcessCrashed'),
#    ('?', '^.*'),
    ]

errors = {}

if args.cases:
    style = Style(colors=('#00ff00', '#ffa000', '#ff4000', '#ff0000'))
    config = pygal.Config(style=style, show_minor_x_labels=False, truncate_label=11,
                          legend_at_bottom=True)
    c = pygal.StackedBar(config)
    c.title = 'Stress test results over time - cases'
    c.add('always success', [r.cases_ok() for r in results])
    c.add('sporadic failure', [r.cases_fail('flaky') for r in results])
    c.add('varying failures', [r.cases_fail('inconsistent') for r in results])
    c.add('same failure always', [r.cases_fail('broken') for r in results])
else:
    config = pygal.Config(show_minor_x_labels=False, truncate_label=11,
                          legend_at_bottom=True)
    c = pygal.StackedBar(config)
    c.title = 'Stress test results over time - where failures happen (1/1000s)'
    for text, re_text in error_locations:
        re_match = re.compile(re_text).match
        for r in results:
            for case in r.cases.values():
                for tr in case.traces:
                    if re_match(tr) is not None:
                        errors[tr] = (text, re_text)
    for r in results:
        for case in r.cases.values():
            for tr in case.traces:
                if tr not in errors:
                    if tr.strip():
                        print('unknown line: %s' % tr, file=sys.stderr)
    for text, re_text in error_locations:
        l = []
        for r in results:
            v = 0
            for case in r.cases.values():
                for tr in case.traces:
                    if errors.get(tr, [''])[0] == text:
                        v = v + 1
            t = r.total()
            v = int(1000.0 * v / t)
            l.append(v)
        c.add(text, l)

c.x_labels = uniquify(args.directory)
c.x_labels_major = list(startify(c.x_labels))
os.write(sys.stdout.fileno(), c.render())
