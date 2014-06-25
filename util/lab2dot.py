#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: lab2dot.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Wed Jun 25 14:50:02 2014 mstenber
# Last modified: Wed Jun 25 15:03:28 2014 mstenber
# Edit time:     11 min
#
"""

This is (very minimalist) lab.conf => Graphviz dot filter.

Notably, there's only two things in lab.conf we care about:

- node definition
 # node[template]=templatename

and

- interface mapping
 node[ifnumber]=netname

"""

import case2lab
import dot

class LabProcessor(case2lab.ReCollectionProcessor):
    def __init__(self):
        case2lab.ReCollectionProcessor.__init__(self)
        self.dot = dot.DotGraph()
    parse_template_text=r'^\#\s*(\S+)\[template\]\s*=\s*(\S+)$\s*$'
    def parse_template(self, m):
        nodename, templatename = m.groups()
        self.dot.node(nodename, label='"%s [%s]"' % (nodename, templatename),
                      shape='box')
    parse_if_text=r'^(\S+)\[([0-9])+\]=(\S+)$\s*$'
    def parse_if(self, m):
        nodename, ifnumber, netname = m.groups()
        self.dot.transition(nodename, netname, label=str(ifnumber))
    parse_zzz_text='^.*$'
    def parse_zzz(self, m):
        pass

if __name__ == '__main__':
    import sys
    p = LabProcessor()
    p.processLines(sys.stdin)
    print p.dot.dump()
