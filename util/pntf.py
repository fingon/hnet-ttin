#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: pntf.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Mon Mar 24 13:44:24 2014 mstenber
# Last modified: Mon Mar 24 16:50:59 2014 mstenber
# Edit time:     123 min
#
"""

Python Netkit Testing Framework.

Basic idea:

- using a set of step sequences, execution of which are synchronous,
    define a set of tests and test suites.

- within step, have wildly asynchronous behavior: monitor log files,
    execute commands on VMs

(In principle, could have reused e.g. unittest or nose; but in
practise, the amouont of glue code is small, and the asyncio magic
involved is the hairy part).

The datastructures are defined to be highly composable, with access to
their 'parent' objects. The test runner is just responsible for firing
up the root level objects, and ultimately execution is up to set of
test steps.

"""

import asyncio
import logging
import concurrent.futures

_logger = logging.getLogger('pntf')
_debug = _logger.debug
_info = _logger.info

class Named:
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        if self.name:
            n = '"%s"' % self.name
        else:
            n = '0x%s' % id(self)
        v = self.reprValues()
        if v:
            v = ' %s' % repr(v)
        else:
            v = ''
        return '<%s %s%s>' % (self.__class__.__name__, n, v)
    def reprValues(self):
        return {}

class Step(Named):
    def __init__(self,
                 command,
                 *,
                 name=None,
                 pre=None, failPre=None,
                 post=None, failPost=None,
                 timeout=None,
                 exceptionIsFailure=False):
        Named.__init__(self, name)
        self.command = command
        self.pre = pre
        self.failPre = failPre
        self.post = post
        self.failPost = failPost
        self.timeout = timeout
        self.exceptionIsFailure = exceptionIsFailure
    def run(self, state=None):
        _debug('%s run()' % repr(self))
        if self.pre:
            r = yield from self.runAsync(state, self.pre, self.failPre)
            if r != 0:
                _info('%s precondition failed: %s' % (repr(self),
                                                      repr(pre)))
                return False
        r = yield from self.runAsync(state, self.command)
        if r != 0:
            _info('%s failed: %s' % (repr(self), repr(self.command)))
            return False
        if self.post:
            r = yield from self.runAsync(state, self.post, self.failPost)
            if r != 0:
                _info('%s postcondition failed: %s' % (repr(self),
                                                       repr(post)))
                return False
        return True
    def runAsync(self, state, *args):
        l = filter(None, args)
        assert l, 'must have at least one job'
        l = list(map(lambda x:asyncio.Task(x(state or self)), l))
        done, pending = yield from asyncio.wait(l, timeout=self.timeout,
                                                return_when=concurrent.futures.FIRST_COMPLETED)
        _debug('runAsync => %s' % repr(done))
        for i, o in enumerate(l):
            _debug('considering %s' % repr(o))
            if o and o in done:
                if self.exceptionIsFailure:
                    e = o.exception()
                    if e:
                        _info('exception %s occurred in %s' % (repr(e),
                                                               repr(o)))
                        return
                if o.result():
                    return i
                return
        return

class StepSequence(Named):
    def __init__(self, steps, *, name=None):
        Named.__init__(self, name)
        self.steps = steps
    def run(self, state=None):
        for i, o in enumerate(self.steps):
            _debug('%s running step #%d: %s' % (repr(self),i,repr(o)))
            r = yield from o.run(state)
            if not r:
                _info("%s step #%d failed" % (repr(self), i))
                return False
        return True

class TestCase(Named):
    def __init__(self, main, *, name=None, setup=None, tearDown=None):
        Named.__init__(self, name)
        self.main = main
        self.setup = setup
        self.tearDown = tearDown
    def run(self, state=None):
        _debug('%s run()' % repr(self))
        r = True
        if self.setup:
            r = self.runOne(state, self.setup)
        if r:
            r = self.runOne(state, self.main)
        # We run tearDown always, even if we never ran the main sequence
        if self.tearDown:
            r = self.runOne(state, self.tearDown)
        _debug('%s run() result %s' % (repr(self), repr(r)))
        return r
    def runOne(self, state, x):
        try:
            iter(x)
            x = StepSequence(list(x))
        except:
            pass
        if isinstance(x, Step):
            x = StepSequence([x])
        if isinstance(x, StepSequence):
            r = yield from x.run(state or self)
            return r
        raise NotImplementedError

# TestSuite == StepSequence. Brilliant!
def run(*args):
    loop = asyncio.get_event_loop()
    for i, arg in enumerate(args):
        _debug('run() running #%d:%s' % (i, repr(arg)))
        loop.run_until_complete(arg())

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--debug', action='store_true')
    ap.add_argument('--verbose', action='store_true')

    DELAY=0.01
    args = ap.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
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
    @asyncio.coroutine
    def _t():
        f1 = Step(sleeperFail1)
        s1 = Step(sleeperOk1)
        a1 = Step(assertFail1, exceptionIsFailure=True)
        cmds = [0,0,0,0]

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

        cmds = [0,0,0,0]
        r = yield from TestCase(StepSequence([s1, s1])).run(cmds)
        assert r
        assert cmds[0] == 2

        # Shortened form
        cmds = [0,0,0,0]
        r = yield from TestCase([s1, s1]).run(cmds)
        assert r
        assert cmds[0] == 2
    run(_t)

