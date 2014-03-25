#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: cotest.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Mon Mar 24 13:44:24 2014 mstenber
# Last modified: Tue Mar 25 10:38:27 2014 mstenber
# Edit time:     140 min
#
"""

(Python) Coroutine-based Testing Framework.

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

_logger = logging.getLogger('cotest')
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
                 failIf=None,
                 name=None,
                 timeout=None,
                 exceptionIsFailure=False):
        Named.__init__(self, name)
        self.command = command
        self.failIf = failIf
        self.timeout = timeout
        self.exceptionIsFailure = exceptionIsFailure
    def run(self, state=None):
        _debug('%s run()' % repr(self))
        r = yield from self.runAsync(state, self.command, self.failIf)
        if r != 0:
            _info('%s failed: %s' % (repr(self), repr(self.command)))
            return False
        return True
    def runAsync(self, state, *args):
        assert args, 'must have at least one job'
        def _convert(x):
            r = x(state or self)
            _debug('starting %s => %s' % (repr(x), repr(r)))
            if r and asyncio.iscoroutine(r):
                return asyncio.Task(r)
            return r
        args = filter(None, args)
        l = list(map(_convert, args))
        # If there was immediate response, process it
        for i, o in enumerate(l):
            if not isinstance(o, asyncio.Task):
                if o:
                    return i
                return
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
    def __init__(self, steps, *, name=None, stopFail=True):
        Named.__init__(self, name)
        self.steps = steps
        self.stopFail = stopFail
    def run(self, state=None):
        r = True
        for i, o in enumerate(self.steps):
            _debug('%s running step #%d: %s' % (repr(self),i,repr(o)))
            cr = yield from o.run(state)
            if not cr:
                _info("%s step #%d failed" % (repr(self), i))
                if self.stopFail:
                    return False
                r = False
        return r

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
    pass
