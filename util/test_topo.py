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
# Last modified: Tue Mar 25 16:33:55 2014 mstenber
# Edit time:     15 min
#
"""

These are unittest-style tests which leverage cotest and cotest_ttin
underneath to make sure the test topology(/topologies) work correctly.

"""

import unittest
import cotest
from cotest_ttin import *

# XXX - validate address lifetimes at client

class TestBasic(unittest.TestCase):
    def test_base(self):
        tc = cotest.TestCase(base_test)
        assert cotest.run(tc)
    def test_ula(self):
        l = [startTopology('bird7', 'obird', ispTemplate='isp')] + base_6_local_test
        tc = cotest.TestCase(l)
        assert cotest.run(tc)
    def test_4only(self):
        l = [startTopology('bird7', 'obird', ispTemplate='isp4')] + base_4_test
        tc = cotest.TestCase(l)
        assert cotest.run(tc)
    def test_6only(self):
        l = [startTopology('bird7', 'obird', ispTemplate='isp6')] + base_6_test
        tc = cotest.TestCase(l)
        assert cotest.run(tc)
    def test_6rd(self):
        l = [startTopology('bird7', 'obird', ispTemplate='isp4-6rd')] + base_6_test + base_4_test
        tc = cotest.TestCase(l)
        assert cotest.run(tc)
    def test_6rd_6(self):
        l = [startTopology('bird7', 'obird', ispTemplate='isp4-6rd-6')] + base_6_test + base_4_test
        # XXX - add checks to make sure we have both 6rd and non-6rd addresses
        tc = cotest.TestCase(l)
        assert cotest.run(tc)

class TestMH(unittest.TestCase):
    def test_mh(self):
        l = [startTopology('mhbird10', 'obird')] + base_6_test
        tc = cotest.TestCase(l)
        assert cotest.run(tc)


class TestNasty(unittest.TestCase):
    def test_mh(self):
        l = [startTopology('bird14', 'obird')] + base_6_test + base_4_test
        tc = cotest.TestCase(l)
        assert cotest.run(tc)

if __name__ == '__main__':
    #logging.basicConfig(level=logging.DEBUG)
    unittest.main()

