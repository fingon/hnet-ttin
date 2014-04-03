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
# Last modified: Thu Apr  3 13:46:23 2014 mstenber
# Edit time:     83 min
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
    def test(self):
        l = base_test[:]
        l[0] = startTopology(self.topology, self.router)
        tc = cotest.TestCase(l)
        assert cotest.run(tc)
    def test_ula(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp'),
             waitRouterPrefix6('fd')] + base_6_local_test
        # + fw_test - not relevant - no outside!
        tc = cotest.TestCase(l)
        assert cotest.run(tc)
    def test_4only(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp4')]
        l = l + base_4_test + base_6_local_test + fw_test
        tc = cotest.TestCase(l)
        assert cotest.run(tc)
    def test_6only(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp6')]
        l = l + base_6_test + fw_test
        l = l + [nodeHasPrefix6('client', '2000:')]
        tc = cotest.TestCase(l)
        assert cotest.run(tc)
    def test_6only_inf_ifdown(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp6-inf')]
        l = l + base_6_test + fw_test
        l = l + [nodeHasPrefix6('client', '2000:')]
        # Kill ipv6 uplink -> should disappear from client's preferred addresses in a minute
        #l = l + [nodeRun('cpe', 'ifdown h1_6')]
        l = l + [nodeRun('cpe', 'ifconfig eth1 down')]
        l = l + [cotest.RepeatStep(cotest.NotStep(nodeHasPrefix6('client', '2000:')),
                                   timeout=60, wait=1)]

        tc = cotest.TestCase(l)
        assert cotest.run(tc)

    def test_6rd(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp4-6rd')]
        l = l + base_6_test + base_4_test + fw_test
        l = l + [nodeHasPrefix6('client', '2001:')]
        tc = cotest.TestCase(l)
        assert cotest.run(tc)
    def test_6rd_6(self):
        l = [startTopology(self.topology, self.router,
                           ispTemplate='isp4-6rd-6'),
             cotest.RepeatStep(updateNodeAddresses6('client', minimum=2),
                               wait=5, timeout=60),
             ]
        l = l + base_6_test + base_4_test + fw_test
        l = l + [nodeHasPrefix6('client', '2000:'),
                 nodeHasPrefix6('client', '2001:')]
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
        l = l + [nodeHasPrefix6('client', '2000:dead:'),
                 nodeHasPrefix6('client', '2000:cafe:'),
                 nodeHasPrefix6('client', '2000:beef:')]

        tc = cotest.TestCase(l)
        assert cotest.run(tc)

class MHFallback(MH):
    router = 'obird-debug'

class Lease(unittest.TestCase):
    def test(self):
        l = base_test[:]
        # initially, make sure stuff works as normal
        l = l + [sleep(700)] # even valid <= 600
        # then, make sure things still work
        # (Can't use base_4_test, as it assumes client is not configured)
        l = l + base_6_test + base_4_postsetup_test + fw_test
        tc = cotest.TestCase(l)
        assert cotest.run(tc)

class LeaseFallback(Lease):
    router = 'obird-debug'

class Large(unittest.TestCase):
    topology = 'bird14'
    router = 'obird'
    def setUp(self):
        l = base_test[:]
        l[0] = startTopology(self.topology, self.router)
        self.l = l
    def test(self):
        tc = cotest.TestCase(self.l)
        assert cotest.run(tc)
    def test_mutation(self):
        # Initial route should include bird9
        l = self.l

        # without traceroute6, this is somewhat ardurous to test..
        #has_b9 = nodeTraceroute6Contains('client', 'h-server', b'bird9.')
        #l = l + [has_b9]

        # Then we kill bird9, and wait for things to work again
        # (HNCP has built-in 4 minute delay currently it seems)
        l = l + [nodeStop('bird9')] + [sleep(180)]
        l = l + base_6_test + base_4_postsetup_test

        # Resume bird9, kill two other routes, and should go up
        # 'faster' because routes are better (no waiting 180 seconds)
        l = l + [nodeGo('bird9'), nodeStop('bird4'), nodeStop('bird6')]
        l = l + base_6_test + base_4_postsetup_test
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

