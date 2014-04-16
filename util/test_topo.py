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
# Last modified: Wed Apr 16 16:33:54 2014 mstenber
# Edit time:     130 min
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
        tc = TestCase(l)
        assert cotest.run(tc)
    def test_ula(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp'),
             waitRouterPrefix6('fd')] + base_6_local_test
        # + fw_test - not relevant - no outside!
        tc = TestCase(l)
        assert cotest.run(tc)
    def test_4only(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp4')]
        l = l + base_4_test + base_6_local_test + fw_test
        tc = TestCase(l)
        assert cotest.run(tc)
    def test_6only(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp6')]
        l = l + base_6_test + fw_test
        l = l + [nodeHasPrefix6('client', '2000:')]
        tc = TestCase(l)
        assert cotest.run(tc)
    def test_6only_64(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp6-64')]
        l = l + [cotest.NotStep(nodeHasPrefix6('client', '2000:'))]
        l = l + [nodeRun('client', 'dhclient -6 eth0')]
        l = l + [nodeHasPrefix6('client', '2000:')]
        l = l + base_6_test + fw_test
        tc = TestCase(l)
        assert cotest.run(tc)
    def test_6only_inf_cpe_isp_down(self):
        # Basic idea: when uplink disappears even with infinite
        # lifetime, it should disappear from the client.
        l = [startTopology(self.topology, self.router, ispTemplate='isp6-inf')]
        l = l + base_6_test + fw_test
        l = l + [nodeHasPrefix6('client', '2000:')]

        # Kill ipv6 uplink -> should disappear from client's preferred
        # addresses in a minute
        #l = l + [nodeRun('cpe', 'ifdown h1_6')]
        l = l + [nodeRun('cpe', 'ifconfig eth1 down')]
        l = l + [cotest.RepeatStep(cotest.NotStep(nodeHasPrefix6('client', '2000:')),
                                   timeout=60, wait=1)]

        tc = TestCase(l)
        assert cotest.run(tc)
    def test_6only_link_down_up(self):
        # Make sure if we ifdown client facing interface, it gets up
        # with same address. We test that by NOT updating the client
        # addresses after ifdown + ifup, but instead rely on it
        # getting same prefix (and routing works).
        l = [startTopology(self.topology, self.router, ispTemplate='isp6')]
        l = l + base_6_test + fw_test
        l = l + [nodeRun('bird3', 'ifdown h1')]
        l = l + [sleep(5)]
        l = l + [nodeRun('bird3', 'ifup h1')]

        # This timeout is sadly long; 15 doesn't seem to be enough as
        # of 2014-04-17..
        l = l + [cotest.RepeatStep(nodePingFromAll6('client', 'h-server'),
                                   wait=1, timeout=30)]
        tc = TestCase(l)
        assert cotest.run(tc)
    def test_6rd(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp4-6rd')]
        l = l + base_6_test + base_4_test + fw_test
        l = l + [nodeHasPrefix6('client', '2001:')]
        tc = TestCase(l)
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
        tc = TestCase(l)
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

        tc = TestCase(l)
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
        l = l + base_6_test + base_4_remote_test + fw_test
        tc = TestCase(l)
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
        tc = TestCase(self.l)
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
        l = l + base_6_test + base_4_remote_test

        # Resume bird9, kill two other routes, and should go up
        # 'faster' because routes are better (no waiting 180 seconds)
        l = l + [nodeGo('bird9'), nodeStop('bird4'), nodeStop('bird6')]
        l = l + base_6_test + base_4_remote_test
        tc = TestCase(l)
        assert cotest.run(tc)


class LargeFallback(Large):
    router = 'obird-debug'

# Specific ~test cases with unique topology

class DownPD(unittest.TestCase):
    topology = 'bird8'
    router = 'obird-debug'
    def test(self):
        # Make sure downstream PD works - client should work even with
        # openwrt node in the middle.
        l = base_test[:]
        l[0] = startTopology(self.topology, self.router)
        # Beyond the router nodes, have to wait for openwrt to get the
        # PD too before running onwards..
        l[2:2] = [cotest.RepeatStep(nodeHasPrefix6('openwrt', '2000'),
                                    wait=1, timeout=TIMEOUT)]
        tc = TestCase(l)
        assert cotest.run(tc)

class Guest(unittest.TestCase):
    topology = 'obird7-guest'
    router = 'obird-debug'
    def test(self):
        # Make sure guest stuff works with remote
        l = [startTopology(self.topology, self.router)] + base_6_remote_test + base_4_setup_test + base_4_remote_test
        # Local stuff shouldn't; however, whether this test really is conclusive about it is another matter
        l = l + [cotest.NotStep(base_6_local_ip_test, timeout=10)]
        l = l + [cotest.NotStep(base_6_local_sd_test, timeout=10)]
        l = l + [cotest.NotStep(base_4_local_test, timeout=10)]
        # XXX - make sure no HNCP and TCP traffic in tcpdump
        tc = TestCase(l)
        assert cotest.run(tc)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)s %(message)s')
    al = logging.getLogger('asyncio')
    al.setLevel(logging.CRITICAL)
    unittest.main()

