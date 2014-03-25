#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: test_cotest.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Tue Mar 25 10:27:35 2014 mstenber
# Last modified: Tue Mar 25 10:38:43 2014 mstenber
# Edit time:     2 min
#
"""

"""

import unittest
from cotest import Step, TestCase, run
import asyncio
import logging

DELAY=0.01

@asyncio.coroutine
def sleeperOk1(cmds):
    yield from asyncio.sleep(DELAY)
    cmds[0] += 1
    assert len(cmds) == 4
    return 1
@asyncio.coroutine
def sleeperOk2(cmds):
    yield from asyncio.sleep(2 * DELAY)
    cmds[1] += 1
    assert len(cmds) == 4
    return 1
@asyncio.coroutine
def sleeperFail1(cmds):
    yield from asyncio.sleep(DELAY)
    cmds[2] += 1
    assert len(cmds) == 4
    return 0
@asyncio.coroutine
def assertFail1(cmds):
    yield from asyncio.sleep(DELAY)
    assert False
@asyncio.coroutine
def sleeperFail2(cmds):
    yield from asyncio.sleep(2 * DELAY)
    cmds[3] += 1
    assert len(cmds) == 4
    return 0
def immediateOk(cmds):
    return 1


class CoTestTest(unittest.TestCase):
    def test_base(self):
        @asyncio.coroutine
        def _t():
            io = Step(immediateOk)
            f1 = Step(sleeperFail1)
            s1 = Step(sleeperOk1)
            a1 = Step(assertFail1, exceptionIsFailure=True)
            cmds = [0,0,0,0]

            r = yield from io.run(cmds)
            assert r

            r = yield from s1.run(cmds)
            assert r

            r = yield from f1.run(cmds)
            assert not r

            r = yield from a1.run(cmds)
            assert not r

            r = yield from TestCase(s1).run(cmds)
            assert r

            # Failing functions should fail
            r = yield from TestCase(f1).run(cmds)
            assert not r

            # Shortened form
            cmds = [0,0,0,0]
            r = yield from TestCase([s1, s1]).run(cmds)
            assert r
            assert cmds[0] == 2
        logging.basicConfig(level=logging.DEBUG)
        run(_t)


if __name__ == '__main__':
    unittest.main()
