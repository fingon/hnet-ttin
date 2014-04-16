#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: hnetd_neigh_changes.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2013 cisco Systems, Inc.
#
# Created:       Thu Feb 28 12:39:13 2013 mstenber
# Last modified: Mon Apr 14 14:48:45 2014 mstenber
# Edit time:     95 min
#
"""

This is utility script which takes a set of syslog.log:s, and produces
a summary of neighbor changes.

The main point is to make changes more ~readable, and more concise,
than what just doing grep + sort would provide.

Input: Set of syslog.log's

Output: ~timeline with each log file either gaining or losing
adjacency shown in rather compact fashion

"""

import re
import datetime

TIMESTAMP_FORMAT='%d-%m-%Y %H:%M:%S'

add_neigh_re = re.compile('^(?P<t>.*) <TRACE>.*New neighbor found: \S+ / (?P<addr>.*) on (?P<ifname>.*)\s*$').match

remove_neigh_re = re.compile('''(?x)
^(?P<t>.*)\s
<TRACE>.*
(?:
Removing\sneighbor
|
Inactivity\stimer\sfired\son\sinterface.*for\sneighbor
)
\s\S+\s/\s(?P<addr>[0-9]\.[0-9]\.[0-9]\.[0-9])\.?\s*$''').match

reconf_re = re.compile('^(?P<t>.*) <INFO> Reconfiguring').match

route_fail_re = re.compile('(?P<t>.*) <TRACE> .*elsai_route_to_rid.*failed').match

route_ok_re = re.compile('(?P<t>.*) <TRACE> .*elsai_route_to_rid.*found').match

def _ts2d(s):
    return datetime.datetime.strptime(s, TIMESTAMP_FORMAT)

class Node:
    def __init__(self, path, name):
        self.path = path
        self.name = name
        self.neigh = {}
        self.timeline = []
        self.route_state = False
        self.route_state_count = 0
        self.route_state_t = None
    def route_fail(self, t):
        self.set_route_state(t, False)
    def route_ok(self, t):
        self.set_route_state(t, True)
    def set_route_state(self, t, st):
        t = _ts2d(t)
        last_t = self.route_state_t
        self.route_state_t = t
        if self.route_state == st:
            self.route_state_count = self.route_state_count + 1
            return
        self.route_state = st
        self.timeline.append((t, 'route state', st,
                              #'repeats of last state', self.route_state_count,
                              'changed within', last_t and t-last_t,
                              ))
    def reconfigure(self, t):
        t = _ts2d(t)
        self.timeline.append((t, 'reconfigure'))
        for addr in self.neigh.keys():
            # reconfigure does NOT apparently kill neighbor
            # relations -> skip

            #self.remove_neigh(t, addr)
            pass
    def add_neigh(self, t, addr, ifname):
        t = _ts2d(t)
        if self.neigh.has_key(addr):
            v = self.neigh[addr]
            v[0] = v[0] + 1
        else:
            self.neigh[addr] = [1, ifname]
        self.timeline.append((t, 'add', addr, ifname))
    def remove_neigh(self, t, addr):
        t = _ts2d(t)
        assert self.neigh.has_key(addr), 'no %s for %s in %s' % (addr, self.name, self.neigh)
        v = self.neigh[addr]
        v[0] = v[0] - 1
        if v[0] == 0:
            del self.neigh[addr]
        self.timeline.append((t, 'remove', addr))
    def peek(self):
        if len(self.timeline)>0:
            return self.timeline[0]
    def pop(self):
        t = self.timeline[0]
        del self.timeline[0]
        return t
    def count(self):
        return len(self.neigh)

def analyze_files(filelist):
    nodes = []
    i = 1
    for filename in filelist:
        #print 'handling', filename
        name = '%d' % i
        node = Node(filename, name)
        print name, filename
        for line in open(filename):
            line = line.strip()

            m = add_neigh_re(line)
            if m is not None:
                gr = m.groupdict()
                #print 'match add', gr
                node.add_neigh(gr['t'], gr['addr'], gr['ifname'])

            m = remove_neigh_re(line)
            if m is not None:
                gr = m.groupdict()
                #print 'match remove 1', gr, line
                node.remove_neigh(gr['t'], gr['addr'])

            m = reconf_re(line)
            if m is not None:
                gr = m.groupdict()
                node.reconfigure(gr['t'])

            m = route_fail_re(line)
            if m is not None:
                gr = m.groupdict()
                node.route_fail(gr['t'])

            m = route_ok_re(line)
            if m is not None:
                gr = m.groupdict()
                node.route_ok(gr['t'])


        nodes.append(node)
        i = i + 1
    orig = None
    while 1:
        t = None
        n = None
        for node in nodes:
            nt = node.peek()
            if nt:
                if not t or t[0] > nt[0]:
                    n = node
                    t = nt
        if not t:
            print 'End of timeline'
            break
        if orig is None:
            orig = t[0]
            now = orig
        else:
            now = t[0]
        n.pop()
        delta = now - orig
        print n.name, delta, t[1:]
    c = 0
    for node in nodes:
        c = c + node.count()
    print 'Total of %d neighbor relations among %d nodes' % (c, len(nodes))

if __name__ == '__main__':
    import sys
    analyze_files(sys.argv[1:])
