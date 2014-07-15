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
# Last modified: Tue Jul 15 18:31:34 2014 mstenber
# Edit time:     1 min
#
"""

Slow versions of test_topo tests; notably, some flakiness happens
usually just sometimes, and for that, high iteration counts _within
same test_ may help.

"""

import test_topo
import unittest

class MutateSlow(test_topo.Mutate):
    iterations = 50

class MutateFallbackSlow(test_topo.MutateFallback):
    iterations = 50

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)s %(message)s')
    al = logging.getLogger('asyncio')
    al.setLevel(logging.CRITICAL)
    unittest.main()
