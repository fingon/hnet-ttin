#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: dump_bier.py $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Copyright (c) 2015 Markus Stenberg
#
# Created:       Sun Mar 22 19:45:36 2015 mstenber
# Last modified: Sun Mar 22 20:30:30 2015 mstenber
# Edit time:     8 min
#
"""

Jokingly named module to convert hnet-dump to bier module parameters.

Can be used in e.g. rmmod + insmod thing..

"""

import json
import os
import sys

d = json.load(sys.stdin)
nid = d['node-id']
l = []
for i, (k, nd) in enumerate(d['nodes'].items()):
    if k == nid:
        print 'bid=%d' % i
    for e in nd.get('addresses', []):
        addr = e['address']
        if '.' in addr:
            continue
        a = os.popen('ipv6calc -I ipv6addr -O ifinet6 %s' % addr).read().split(' ')[0]
        l.append(a)
        break
    else:
        l.append('00' * 16)
print 'biarr=%s' % (','.join(l))



