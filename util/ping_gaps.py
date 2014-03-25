#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: ping_gaps.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2013 cisco Systems, Inc.
#
# Created:       Wed Oct 30 17:18:47 2013 mstenber
# Last modified: Tue Nov  5 20:08:46 2013 mstenber
# Edit time:     7 min
#
"""

Given output of a ping, look for gaps.

"""

import sys
import re

ping_re = re.compile('icmp_seq=(\d+)\s.*time=').search


last = 0
lastfail = 0
totallost = 0
for line in sys.stdin:
    m = ping_re(line)
    if m:
        seq = int(m.group(1))
        if seq > last+1:
            lost = seq-last-1
            totallost = totallost + lost
            print seq, 'Missing', lost, 'after successful', seq-lastfail
            lastfail = seq
        last = seq
print 'Lost packets', totallost, 'out of', seq
