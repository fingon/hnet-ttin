#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: test_topo.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Tue Mar 25 15:52:19 2014 mstenber
# Last modified: Thu Mar 27 13:53:00 2014 mstenber
# Edit time:     56 min
#
"""

These are unittest-style tests which leverage cotest and cotest_ttin
underneath to make sure the test topology(/topologies) work correctly.

"""

import unittest
import cotest
from cotest_ttin import *

# XXX - validate address lifetimes at client

class Basic(unittest.TestCase):
    topology = 'bird7'
    router = 'obird'
    def test_base(self):
        tc = cotest.TestCase(base_test)
        assert cotest.run(tc)
    def test_ula(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp'),
             waitRouterPrefix6('fd')] + base_6_local_test + fw_test
        tc = cotest.TestCase(l)
        assert cotest.run(tc)
    def test_4only(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp4')]
        l = l + base_4_test + fw_test
        tc = cotest.TestCase(l)
        assert cotest.run(tc)
    def test_6only(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp6')]
        l = l + base_6_test + fw_test
        l = l + [nodeHasPrefix('client', '2000:')]
        tc = cotest.TestCase(l)
        assert cotest.run(tc)
    def test_6rd(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp4-6rd')]
        l = l + base_6_test + base_4_test + fw_test
        l = l + [nodeHasPrefix('client', '2001:')]
        tc = cotest.TestCase(l)
        assert cotest.run(tc)
    def test_6rd_6(self):
        l = [startTopology(self.topology, self.router,
                           ispTemplate='isp4-6rd-6'),
             cotest.RepeatStep(updateNodeAddresses6('client', minimum=2),
                               wait=5, timeout=60),
             ]
        l = l + base_6_test + base_4_test
        l = l + [nodeHasPrefix('client', '2000:'),
                 nodeHasPrefix('client', '2001:')]
        tc = cotest.TestCase(l)
        assert cotest.run(tc)

class BasicFallback(Basic):
    router = 'obird-debug'

class MH(unittest.TestCase):
    topology = 'mhbird10'
    router = 'obird'
    def test(self):
        l = [startTopology(self.topology, self.router),
               cotest.RepeatStep(updateNodeAddresses6('client', minimum=3),
                                 wait=5, timeout=60)]
        l = l + base_6_test
        l = l + [nodeHasPrefix('client', '2000:dead:'),
                 nodeHasPrefix('client', '2000:cafe:'),
                 nodeHasPrefix('client', '2000:beef:')]

        tc = cotest.TestCase(l)
        assert cotest.run(tc)

class MHFallback(MH):
    router = 'obird-debug'

class Large(unittest.TestCase):
    topology = 'bird14'
    router = 'obird'
    l = [startTopology(self.topology, self.router)]
    l = l + base_6_test + base_4_test
    def test(self):
        tc = cotest.TestCase(self.l)
        assert cotest.run(tc)
    def test_mutation(self):
        # Initial route should include bird9
        l = self.l[:]

        # without traceroute6, this is somewhat ardurous to test..
        #has_b9 = nodeTraceroute6Contains('client', 'h-server', b'bird9.')
        #l = l + [has_b9]

        # Then we kill bird9, and wait for things to work again
        l = l + [nodeStop('bird9')] + base_6_test + base_4_test
        #l = l + [NotStep(has_b9)]

        # Resume bird9, and it should be there again..
        #l = l + [nodeGo('bird9'),
        #         cotest.RepeatStep(has_b9, wait=5, timeout=120)]
        #l = l + base_6_test + base_4_test
        tc = cotest.TestCase(l)
        assert cotest.run(tc)

    def test_lease(self):
        l = self.l[:]
        # initially, make sure stuff works as normal
        l = l + [sleep(700)] # even valid <= 600
        # then, make sure things still work
        l = l + base_6_test + base_4_test
        tc = cotest.TestCase(l)
        assert cotest.run(tc)

class LargeFallback(Large):
    router = 'obird-debug'


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)s %(message)s')
    al = logging.getLogger('asyncio')
    al.setLevel(logging.CRITICAL)
    unittest.main()

