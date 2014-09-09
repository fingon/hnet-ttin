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
# Last modified: Tue Sep  9 10:21:21 2014 mstenber
# Edit time:     250 min
#
"""

These are unittest-style tests which leverage cotest and cotest_ttin
underneath to make sure the test topology(/topologies) work correctly.

"""

import unittest
import cotest
from cotest_ttin import *
import ipaddress
import logging

_logger = logging.getLogger('test_topo')
_debug = _logger.debug
_info = _logger.info


# XXX - validate address lifetimes at client
class Basic(unittest.TestCase):
    topology = 'home7'
    router = 'owrt-router'
    def test(self):
        l = base_tests[:]
        l[0] = startTopology(self.topology, self.router)
        tc = TestCase(l)
        assert cotest.run(tc)
    def test_ula(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp'),
             waitRouterPrefix6('fd')] + base_6_local_sd_test
        # local_ip isn't applicable as no GUA and it checks for non-fd::/8
        # + fw_test - not relevant - no outside!
        tc = TestCase(l)
        assert cotest.run(tc)
    def test_4only(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp4')]
        l = l + base_4_tests + base_6_local_tests + fw_test
        l.remove(base_6_local_ip_step) # We won't have GUA
        tc = TestCase(l)
        assert cotest.run(tc)
    def test_6only(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp6')]
        l = l + base_6_tests + fw_test
        l = l + [nodeHasPrefix6('client', '2000:')]
        tc = TestCase(l)
        assert cotest.run(tc)
    def test_6only_64(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp6-64')]
        l = l + [cotest.NotStep(nodeHasPrefix6('client', '2000:'))]
        l = l + [nodeRun('client', 'dhclient -6 eth0')]
        l = l + [nodeHasPrefix6('client', '2000:')]
        l = l + base_6_tests + fw_test
        tc = TestCase(l)
        assert cotest.run(tc)
    def test_6only_62(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp6-62')]
        l = l + [cotest.NotStep(nodeHasPrefix6('client', '2000:'))]
        l = l + [nodeRun('client', 'dhclient -6 eth0')]
        l = l + [nodeHasPrefix6('client', '2000:')]
        l = l + base_6_tests + fw_test
        tc = TestCase(l)
        assert cotest.run(tc)
    def test_6only_inf_cpe_isp_down(self):
        # Basic idea: when uplink disappears even with infinite
        # lifetime, it should disappear from the client.
        l = [startTopology(self.topology, self.router, ispTemplate='isp6-inf')]
        l = l + base_6_tests + fw_test
        l = l + [nodeHasPrefix6('client', '2000:')]

        # Kill ipv6 uplink -> should disappear from client's preferred
        # addresses in a minute
        #l = l + [nodeRun('cpe', 'ifdown h1_6')]
        l = l + [nodeRun('cpe', 'ifconfig eth1 down')]
        l = l + [cotest.RepeatStep(cotest.NotStep(nodeHasPrefix6('client', '2000:')),
                                   timeout=TIMEOUT, wait=1)]

        tc = TestCase(l)
        assert cotest.run(tc)
    def test_6only_link_down_up(self):
        # Make sure if we ifdown client facing interface, it gets up
        # with same address. We test that by NOT updating the client
        # addresses after ifdown + ifup, but instead rely on it
        # getting same prefix (and routing works).
        l = [startTopology(self.topology, self.router, ispTemplate='isp6')]
        l = l + base_6_tests + fw_test
        l = l + [nodeRun('ir3', 'ifdown h1')]
        l = l + [sleep(5)]
        l = l + [nodeRun('ir3', 'ifup h1')]

        # This timeout is sadly long; 15 doesn't seem to be enough as
        # of 2014-04-17..
        l = l + [cotest.RepeatStep(nodePingFromAll6('client', 'h-server'),
                                   wait=1, timeout=TIMEOUT)]
        tc = TestCase(l)
        assert cotest.run(tc)
    def test_6rd(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp4-6rd')]
        l = l + base_6_tests + base_4_tests + fw_test
        l = l + [nodeHasPrefix6('client', '2001:')]
        tc = TestCase(l)
        assert cotest.run(tc)
    def test_6rd_6(self):
        l = [startTopology(self.topology, self.router,
                           ispTemplate='isp4-6rd-6'),
             cotest.RepeatStep(updateNodeAddresses6('client', minimum=2),
                               wait=5, timeout=TIMEOUT),
             ]
        l = l + base_6_tests + base_4_tests + fw_test
        l = l + [nodeHasPrefix6('client', '2000:'),
                 nodeHasPrefix6('client', '2001:')]
        tc = TestCase(l)
        assert cotest.run(tc)

class BasicFallback(Basic):
    router = 'owrt-router-debug'

class MH(unittest.TestCase):
    topology = 'home10-3isp'
    router = 'owrt-router'
    def test(self):
        l = [startTopology(self.topology, self.router),
               cotest.RepeatStep(updateNodeAddresses6('client', minimum=3),
                                 wait=5, timeout=TIMEOUT)]
        l = l + base_6_tests
        l = l + [nodeHasPrefix6('client', '2000:dead:'),
                 nodeHasPrefix6('client', '2000:cafe:'),
                 nodeHasPrefix6('client', '2000:beef:')]

        tc = TestCase(l)
        assert cotest.run(tc)

class MHFallback(MH):
    router = 'owrt-router-debug'

class Lease(unittest.TestCase):
    def test(self):
        l = base_tests[:]
        # initially, make sure stuff works as normal
        l = l + [sleep(700)] # even valid <= 600
        # then, make sure things still work
        # (Can't use base_4_tests as is, as it assumes client is not configured)
        tl = base_4_tests[:]
        tl.remove(base_4_setup_test)
        l = l + base_6_tests + tl + fw_test
        tc = TestCase(l)
        assert cotest.run(tc)

class LeaseFallback(Lease):
    router = 'owrt-router-debug'

class Large(unittest.TestCase):
    topology = 'home14'
    router = 'owrt-router'
    def setUp(self):
        l = base_tests[:]
        # Large topology seems to take long time to start, sometimes
        l[0] = [startTopology(self.topology, self.router),
                waitRouterPrefix6('200', wait=5, timeout=300)]
        self.l = l
    def test(self):
        tc = TestCase(self.l)
        assert cotest.run(tc)
    def test_mutation(self):
        # Initial route should include ir9
        l = self.l

        # without traceroute6, this is somewhat ardurous to test..
        #has_b9 = nodeTraceroute6Contains('client', 'h-server', b'ir9.')
        #l = l + [has_b9]

        # Then we kill ir9, and wait for things to work again
        # (HNCP has built-in 4 minute delay currently it seems)
        l = l + [nodeStop('ir9')] #+ [sleep(180)]
        # after adding ping_interval 10, the route should die in ~10 seconds
        # => should fit well within normal failure parameters
        l = l + base_6_tests + base_4_remote_tests

        # Resume ir9, kill two other routes, and should go up
        # 'faster' because routes are better (no waiting 180 seconds)
        l = l + [nodeGo('ir9'), nodeStop('ir4'), nodeStop('ir6')]
        l = l + base_6_tests + base_4_remote_tests
        tc = TestCase(l)
        assert cotest.run(tc)


class LargeFallback(Large):
    router = 'owrt-router-debug'

# Specific ~test cases with unique topology

class DownPD(unittest.TestCase):
    topology = 'home8'
    router = 'owrt-router-debug'
    def test(self):
        # Make sure downstream PD works - client should work even with
        # openwrt node in the middle.
        l = base_tests[:]
        l[0] = startTopology(self.topology, self.router)
        # Beyond the router nodes, have to wait for openwrt to get the
        # PD too before running onwards..
        l[1:1] = [cotest.RepeatStep(nodeHasPrefix6('openwrt', '2000'),
                                    wait=1, timeout=TIMEOUT)]
        # PCP tests are not relevant in this case; quite the opposite,
        # they _are_ bound to fail.
        l.remove(base_6_remote_pcp_test)
        l.remove(base_4_remote_pcp_test)
        tc = TestCase(l)
        assert cotest.run(tc)

class Guest(unittest.TestCase):
    topology = 'home7-owrt-guest'
    router = 'owrt-router-debug'
    def test(self):
        # Make sure guest stuff works with remote
        l = [startTopology(self.topology, self.router)] + base_6_remote_tests + base_4_setup_test + base_4_remote_tests
        # Local stuff shouldn't; however, whether this test really is conclusive about it is another matter
        l = l + [cotest.NotStep(base_6_local_ip_step, timeout=TIMEOUT_SHORT)]
        l = l + [cotest.NotStep(base_6_local_sd_test, timeout=TIMEOUT_SHORT)]
        l = l + [cotest.NotStep(base_4_local_test, timeout=TIMEOUT_SHORT)]
        # XXX - make sure no HNCP and TCP traffic in tcpdump
        tc = TestCase(l)
        assert cotest.run(tc)

class Hybrid(unittest.TestCase):
    topology = 'home7-owrt-hybrid'
    router = 'owrt-router'
    tests_6 = [base_6_remote_ping_test, # PCP N/A probably
               base_6_local_ip_step,
               cotest.RepeatStep(nodePing6('client', 'ir2.h1.ir2.home'),
                                 wait=1, timeout=TIMEOUT)]
    tests_4 = [base_4_setup_test, base_4_remote_ping_test,
               cotest.RepeatStep(nodePing4('client', 'ir2.h1.ir2.home'),
                                 wait=1, timeout=TIMEOUT)]
    def test(self):
        l = [startTopology(self.topology, self.router)]
        l = l + self.tests_6 + self.tests_4
        tc = TestCase(l)
        assert cotest.run(tc)
    def test_4only(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp4')]
        l = l + self.tests_4
        tc = TestCase(l)
        assert cotest.run(tc)
    @unittest.skip('current default OpenWrt cannot handle IPv6-only ISP')
    def test_6only(self):
        l = [startTopology(self.topology, self.router, ispTemplate='isp6')]
        l = l + self.tests_6
        tc = TestCase(l)
        assert cotest.run(tc)


class HybridFallback(Hybrid):
    router = 'owrt-router-debug'

class Adhoc(unittest.TestCase):
    topology = 'home7-owrt-adhoc'
    router = 'owrt-router-adhoc'
    def test(self):
        l = base_tests[:]
        l[0] = startTopology(self.topology, self.router)
        tc = TestCase(l)
        assert cotest.run(tc)

class AdhocFallback(Adhoc):
    router = 'owrt-router-debug-adhoc'

class Custom(unittest.TestCase):
    topology = 'home7-owrt-custom'
    router = 'owrt-router'
    def test(self):
        l = [startTopology(self.topology, self.router)]
        l = l + [cotest.RepeatStep(nodeHasPrefix6('client', '200'),
                                   wait=1, timeout=TIMEOUT)]

        l = l + base_6_remote_tests
        l = l + [nodeRun('client', 'dhclient eth0')]
        l = l + [waitRouterPrefix4('172.', timeout=TIMEOUT_INITIAL)]
        l = l + base_4_remote_tests
        l = l + [cotest.RepeatStep(nodePing6('client', 'cpe.h0.test'), wait=1, timeout=TIMEOUT_SHORT),
                 cotest.RepeatStep(nodePing4('client', 'cpe.h0.test'), wait=1, timeout=TIMEOUT_SHORT),
                 cotest.RepeatStep(nodePing6('client', '2000:dead:bee0:70::42'), wait=1, timeout=TIMEOUT_SHORT),
                 cotest.RepeatStep(nodePing4('client', '172.23.0.13'), wait=1, timeout=TIMEOUT_SHORT),
                 ]
        tc = TestCase(l)
        assert cotest.run(tc)

def ensureNoSamePrefix6(h1, i1, h2, i2):
    c1 = CMD_IP6_ADDRS_BASE % ('dev %s' % i1)
    c2 = CMD_IP6_ADDRS_BASE % ('dev %s' % i2)
    a1 = updateNodeAddresses6(h1, cmd=c1, stripPrefix=False)
    a2 = updateNodeAddresses6(h2, cmd=c2, stripPrefix=False)
    def _run(state):
        l1 = state['nodes'][h1]['addrs']
        l2 = state['nodes'][h2]['addrs']
        _debug('ensureNoSamePrefix6 %s <> %s' % (l1, l2))
        for a1 in l1:
            n1 = ipaddress.ip_network(a1, strict=False)
            for a2 in l2:
                n2 = ipaddress.ip_network(a2, strict=False)
                if n1 == n2:
                    return False
        return True
    return [a1, a2, cotest.Step(_run, name='ensure no same v6 prefix')]

class Mutate(unittest.TestCase):
    topology = 'home7-nsa'
    router = 'owrt-router'
    iterations = 1
    def test_replace(self):
        l = base_tests[:]
        l[0] = startTopology(self.topology, self.router)

        for x in range(self.iterations):
            # Mutate the topology by moving ir3-0 from ROUTER1 to HOME
            l = l + [nodeRun('nsa', 'brctl delif net-ROUTER1 ir3-0'),
                     nodeRun('nsa', 'brctl addif net-HOME ir3-0'),
                     cotest.RepeatStep(nodePing6('client', 'cpe.home', timeout=2), wait=1, timeout=TIMEOUT),
                     cotest.RepeatStep(nodePing4('client', 'cpe.home', timeout=2), wait=1, timeout=TIMEOUT),
                     ]
            # Mutate the topology by moving ir3-0 from HOME to ROUTER1
            l = l + [nodeRun('nsa', 'brctl delif net-HOME ir3-0'),
                     nodeRun('nsa', 'brctl addif net-ROUTER1 ir3-0'),
                     cotest.RepeatStep(nodePing6('client', 'cpe.home', timeout=2), wait=1, timeout=TIMEOUT),
                     cotest.RepeatStep(nodePing4('client', 'cpe.home', timeout=2), wait=1, timeout=TIMEOUT),
                     ]

        tc = TestCase(l)
        assert cotest.run(tc)
    def test_move(self):
        # Christopher Franke-originated test;
        # (Same as test_replace, but using different plug ir3-2)
        # typically ~6 iterations to fail as of 20140715 according to C.F.

        l = base_tests[:]
        l[0] = startTopology(self.topology, self.router)

        # net-ROUTER32 is empty network -> we can remove it here
        l = l + [nodeRun('nsa', 'brctl delif net-ROUTER32 ir3-2')]

        for x in range(self.iterations):
            l = l + [nodeRun('nsa', 'brctl delif net-ROUTER1 ir3-0'),
                     nodeRun('nsa', 'brctl addif net-HOME ir3-2'),
                     cotest.RepeatStep(nodePing6('client', 'cpe.home', timeout=2), wait=1, timeout=TIMEOUT),
                     cotest.RepeatStep(nodePing4('client', 'cpe.home', timeout=2), wait=1, timeout=TIMEOUT),
                     cotest.RepeatStep(ensureNoSamePrefix6('ir3', 'eth0', 'ir1', 'eth1'), wait=1, timeout=TIMEOUT),
                     ]
            l = l + [nodeRun('nsa', 'brctl delif net-HOME ir3-2'),
                     nodeRun('nsa', 'brctl addif net-ROUTER1 ir3-0'),
                     cotest.RepeatStep(nodePing6('client', 'cpe.home', timeout=2), wait=1, timeout=TIMEOUT),
                     cotest.RepeatStep(nodePing4('client', 'cpe.home', timeout=2), wait=1, timeout=TIMEOUT),
                     cotest.RepeatStep(ensureNoSamePrefix6('ir3', 'eth2', 'cpe', 'eth0'), wait=1, timeout=TIMEOUT),
                     ]

        tc = TestCase(l)
        assert cotest.run(tc)

class MutateFallback(Mutate):
    router = 'owrt-router-debug'

class Home4(unittest.TestCase):
    topology = 'ow4'
    router = 'owrt-router-debug'
    def test(self):
        l = [startTopology(self.topology, self.router, originalRouterTemplate='openwrt')]

        # Due to prefix assignment delay, on first-hop router we
        # actually get 200* much before we do here. So add extra wait
        # here. Prefix assignment delay is ~10s-ish
        l = l + [cotest.RepeatStep(nodeHasPrefix6('client', '200'),
                                   wait=1, timeout=TIMEOUT)]

        l = l + base_6_remote_tests
        l = l + [nodeRun('client', 'dhclient eth0')] + base_4_remote_tests
        l = l + [cotest.RepeatStep(nodePing6('client', 'openwrt.h0.openwrt.home'), wait=1, timeout=TIMEOUT_SHORT),
                 cotest.RepeatStep(nodePing4('client', 'openwrt.h0.openwrt.home'), wait=1, timeout=TIMEOUT_SHORT),
                 ]

        tc = TestCase(l)
        assert cotest.run(tc)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)s %(message)s')
    al = logging.getLogger('asyncio')
    al.setLevel(logging.CRITICAL)
    unittest.main()
