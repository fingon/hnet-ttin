#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: test_slow_topo.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Tue Jul 15 18:20:19 2014 mstenber
# Last modified: Wed Jul 16 10:13:50 2014 mstenber
# Edit time:     4 min
#
"""

Slow versions of test_topo tests; notably, some flakiness happens
usually just sometimes, and for that, high iteration counts _within
same test_ may help.

"""

import test_topo
import unittest

# test_move
# typically ~6 iterations to fail as of 20140715 according to C.F.

class MutateSlow(test_topo.Mutate):
    iterations = 10

class MutateFallbackSlow(test_topo.MutateFallback):
    iterations = 10

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)s %(message)s')
    al = logging.getLogger('asyncio')
    al.setLevel(logging.CRITICAL)
    unittest.main()
