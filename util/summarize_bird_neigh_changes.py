#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: summarize_bird_neigh_changes.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2013 cisco Systems, Inc.
#
# Created:       Thu Feb 28 12:39:13 2013 mstenber
# Last modified: Mon Mar 11 11:25:50 2013 mstenber
# Edit time:     21 min
#
"""

This is utility script which takes a set of bird*.log, and produces a
summary of neighbor changes.

The main point is to make changes more ~readable, and more concise,
than what just doing grep + sort would provide.

Input: Set of bird*.log

Output: ~timeline with each log file either gaining or losing
adjacency shown in rather compact fashion

"""

import re

add_neigh_re = re.compile('^(?P<t>.*) <TRACE>.*New neighbor found: (?P<addr>.*) on (?P<ifname>.*)\s*$').match

remove_neigh_re = re.compile('^(?P<t>.*) <TRACE>.*Removing neighbor (?P<addr>.*)\s*$').match


class Node:
    def __init__(self, path, name):
        self.path = path
        self.name = name
        self.neigh = {}
        self.timeline = []
    def add_neigh(self, t, addr, ifname):
        #assert not self.neigh.has_key(addr)
        self.neigh[addr] = ifname
        self.timeline.append((t, 'add', addr))
    def remove_neigh(self, t, addr):
        assert(self.neigh.has_key(addr))
        del self.neigh[addr]
        self.timeline.append((t, 'remove', addr))
    def peek(self):
        if len(self.timeline)>0:
            return self.timeline[0]
    def pop(self):
        t = self.timeline[0]
        del self.timeline[0]
        return t

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
                #print 'match remove', gr
                node.remove_neigh(gr['t'], gr['addr'])
        nodes.append(node)
        i = i + 1
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
        n.pop()
        print n.name, t

if __name__ == '__main__':
    import sys
    analyze_files(sys.argv[1:])
