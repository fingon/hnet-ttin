#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: tlv2svg.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2015 cisco Systems, Inc.
#
# Created:       Wed Feb 18 13:25:46 2015 mstenber
# Last modified: Wed Feb 18 13:49:33 2015 mstenber
# Edit time:     11 min
#
"""

This is an utility that creates (human readable) 'churn' graph about
what is going on in the DNCP network, given single hnetd.log (with
debug enabled). Both local and remote updates are shown.

Time is not really an axis here; just the absolute TLV changes seen.

"""

import re
from collections import defaultdict, Counter
import pygal

tlv_change_re = re.compile('.sd._tlv_cb .*(add|remove) .*id=(\d+),').search
node_set_re = re.compile('dncp_node_set').search


# cut-n-paste from kuvat/kuva2gal.py
class StackedBuilder:
    """ An utility class to build a StackedBar graph. Notable features:
    - can input things in arbitrary order
    - provides for optional sorting of labels
    """
    def __init__(self):
        self.data = defaultdict(Counter)
    def add(self, y, label, v=1):
        self.data[y][label] += v
    def write_to_filename(self, filename, label_order=None, **kw):
        # label_order is comprehensive list of labels. If not present, we
        # dynamically determine it.
        if label_order is None:
            labels = set()
            for yc in self.data.values():
                for l in yc.keys():
                    labels.add(l)
            label_order = list(labels)
            label_order.sort()
        sb = pygal.StackedBar(**kw)
        x_labels = list(self.data.keys())
        x_labels.sort()
        sb.x_labels = x_labels
        for label in label_order:
            sb.add(label, [self.data[y][label] for y in x_labels])
        sb.render_to_file(filename)

import sys
t = 0
sb = StackedBuilder()
for line in sys.stdin:
    if node_set_re(line) is not None:
        t += 1
        continue
    m = tlv_change_re(line)
    if m is not None:
        gr = m.groups()
        sb.add('%03d' % t, '%s %s' % (gr[1], gr[0]))
sb.write_to_filename('tlv2svg.svg')
