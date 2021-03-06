#!/usr/bin/env python3.4
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
# Last modified: Mon Apr  7 14:20:52 2014 mstenber
# Edit time:     33 min
#
"""

"""

import unittest
import cotest
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

class DummyCallable:
    def __init__(self, rv):
        self.rv = rv
        self.calls = 0
    def __call__(self):
        self.calls = self.calls + 1
        return self.rv
    def assertCalls(self, x):
        assert self.calls == x
        self.calls = 0

class CoTestTest(unittest.TestCase):
    def test_base(self):
        @asyncio.coroutine
        def _t():
            io = Step(immediateOk)
            f1 = Step(sleeperFail1)
            s1 = Step(sleeperOk1)
            s2 = Step(sleeperOk2)
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

            s = cotest.NotStep(a1)
            r = yield from s.run(cmds)
            assert r

            print('AndStep 1')

            s = cotest.AndStep(s1, s1)
            r = yield from s.run(cmds)
            assert r

            s = cotest.AndStep(s1, f1)
            r = yield from s.run(cmds)
            assert not r

            s = cotest.OrStep(s1, s1)
            r = yield from s.run(cmds)
            assert r

            # Even later success is ok, as long as it's before timeout
            s = cotest.OrStep(s2, f1)
            r = yield from s.run(cmds)
            assert r

            # If timeout happens before ok, we should fail
            s = cotest.OrStep(s2, f1, timeout=DELAY * 1.5)
            r = yield from s.run(cmds)
            assert not r


            # And obviously, failure is failure
            s = cotest.OrStep(f1, f1)
            r = yield from s.run(cmds)
            assert not r


            r = yield from TestCase(s1).run(cmds)
            assert r

            # Make sure we can feed in just single function
            # (It should be converted to StepSequence, and SS should handle it)
            r = yield from TestCase(sleeperOk1).run(cmds)
            assert r

            # Failing functions should fail
            r = yield from TestCase(f1).run(cmds)
            assert not r

            # Shortened form
            cmds = [0,0,0,0]
            r = yield from TestCase([s1, s1]).run(cmds)
            assert r
            assert cmds[0] == 2
            return True
        assert run(_t)
        # Make sure we can also run simple testcase directly
        assert run(TestCase(immediateOk))
    def test_system(self):
        def _t():
            (rc, stdout, stderr) = yield from cotest.async_system("ls")
            assert stdout
            assert not stderr
            assert rc == 0
            return True
            # Stuff below doesn't seem to serve useful purpose :p
            (rc, stdout, stderr) = yield from cotest.async_system("sleep 1 && ls")
            assert stdout
            assert not stderr
            assert rc == 0
            return True
        assert run(_t)
    def test_exec(self):
        def _t():
            (rc, stdout, stderr) = yield from cotest.async_exec("/bin/ls")
            assert stdout
            assert not stderr
            assert rc == 0
            return True
        assert run(_t)
    def test_state(self):
        def first(state):
            state['foo'] = 1
            return True
        def second(state):
            assert 'foo' in state
            return True
        tc = TestCase([first, second])
        assert run(tc)
    def test_repeat(self):
        def thirdok(state):
            yield from asyncio.sleep(DELAY)
            c = state.get('counter', 0)
            c = c + 1
            state['counter'] = c
            return c == 3
        def _t():
            r = yield from cotest.RepeatStep(thirdok, times=4).run()
            assert r
            r = yield from cotest.RepeatStep(thirdok, times=2).run()
            assert not r
            r = yield from cotest.RepeatStep(thirdok, wait=DELAY, timeout=6*DELAY).run()
            assert r
            r = yield from cotest.RepeatStep(thirdok, wait=DELAY, timeout=3*DELAY).run()
            assert not r
            return True
        assert run(_t)
    def test_setup_teardown(self):
        failSetup = DummyCallable(False)
        okSetup = DummyCallable(True)
        failMain = DummyCallable(False)
        okMain = DummyCallable(True)
        failTearDown = DummyCallable(False)
        okTearDown = DummyCallable(True)
        # setup && (main || !main) => tearDown
        s = cotest.TestCase(okMain, setup=okSetup, tearDown=okTearDown);
        r = yield from s.run()
        okSetup.assertCalls(1)
        okMain.assertCalls(1)
        okTearDown.assertCalls(1)
        assert r

        s = cotest.TestCase(failMain, setup=okSetup, tearDown=okTearDown);
        r = yield from s.run()
        okSetup.assertCalls(1)
        failMain.assertCalls(1)
        okTearDown.assertCalls(1)
        assert not r

        # !setup => nop
        s = cotest.TestCase(okMain, setup=failSetup, tearDown=okTearDown);
        r = yield from s.run()
        failSetup.assertCalls(1)
        okMain.assertCalls(0)
        okTearDown.assertCalls(0)
        assert not r

        # !setup && tearDownAlways => tearDown
        s = cotest.TestCase(okMain, setup=failSetup, tearDown=okTearDown, tearDownAlways=True);
        r = yield from s.run()
        failSetup.assertCalls(1)
        okMain.assertCalls(0)
        okTearDown.assertCalls(1)
        assert not r



if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
