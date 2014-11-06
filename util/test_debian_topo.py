#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: test_debian_topo.py $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Copyright (c) 2014 Markus Stenberg
#
# Created:       Thu Sep 18 17:39:46 2014 mstenber
# Last modified: Thu Nov  6 16:00:50 2014 mstenber
# Edit time:     14 min
#
"""

Debian based topology tests (rather minimal but hey, at least we try).

"""

import test_topo
import unittest
import cotest_ttin

rewrites = {'cpe.h0.cpe.home': 'cpe.eth0.cpe.home',
            'ir3.h0.ir3.home': 'ir3.eth0.ir3.home',
            }

class DebianBasic(test_topo.Basic):
    router = 'router'
    @unittest.skip('no 6rd support in debian image')
    def test_6rd(self):
        pass
    @unittest.skip('no 6rd support in debian image')
    def test_6rd_6(self):
        pass
    def tcRun(self, l):
        l = l[:]
        l[0:0] = [cotest_ttin.addRewrites(rewrites)]
        test_topo.Basic.tcRun(self, l)

class DebianMH(test_topo.MH):
    router = 'router'
    tcRun = DebianBasic.tcRun

class DebianLarge(test_topo.Large):
    router = 'router'
    tcRun = DebianBasic.tcRun

del DebianLarge # this does not work due to netkit failing with bunch of Debian VMs; reason is not known

class DebianDownPD(test_topo.DownPD):
    router = 'router'
    tcRun = DebianBasic.tcRun

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)s %(message)s')
    al = logging.getLogger('asyncio')
    al.setLevel(logging.CRITICAL)
    unittest.main()
