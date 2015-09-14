#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: dns_stress.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2015 cisco Systems, Inc.
#
# Created:       Mon Sep 14 09:09:01 2015 mstenber
# Last modified: Mon Sep 14 15:04:24 2015 mstenber
# Edit time:     23 min
#
"""

Torture test ohp instance.

Idea: use 'dig'.

Assume: home7 topology, given ir3 router address.

Things to check for: other routers
- ir1 (via mDNS)
- client (via DHCP)
- random garbage (failing queries)

"""

import argparse
import random
import os

def torture(server, id, debug=False, test_tcp=False):
    if server:
        server = '@' + server
    else:
        server = ''
    # TBD: add e.g. mode
    i = 0
    while True:
        tcp = 0
        if test_tcp:
            tcp = random.randint(0, 1)
        n = random.randint(0, 2)
        if n == 0:
            q = 'ir1.h0.ir3.home'
            ac = 3
        elif n == 1:
            q = 'client.h1.ir3.home'
            ac = 1
        else:
            q = 'asdf%d.h0.ir3.home' % random.randint(0, 12345678)
            ac = 0
        c = 0
        tcp = tcp and '+tcp' or ''
        cmd = 'dig %(server)s -t any %(server)s %(q)s %(tcp)s' % locals()
        if debug:
            print id, i, 'q', q, 'ac', ac
            print '#', cmd
        for line in os.popen(cmd):
            line = line.strip()
            if not line: continue
            if line[0] == ';': continue
            c += 1
        i += 1
        assert c == ac, '%s iteration #%d failed for %s (%d != %d)' % (id, i, q, ac, c)


p = argparse.ArgumentParser(description='DNS server abuse tool')
p.add_argument('-s', '--server', help='ip address of the server')
p.add_argument('-j', '--jobs', type=int, default=1, help='number of parallel jobs')
p.add_argument('-d', '--debug', action='store_true', help='enable debugging')
p.add_argument('-t', '--tcp', action='store_true', help='test randomly also tcp')
args = p.parse_args()
for x in range(args.jobs):
    if x != args.jobs - 1:
        pid = os.fork()
    else:
        pid = 0
    if not pid:
        torture(args.server, x, args.debug, args.tcp)
