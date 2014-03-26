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
# Last modified: Wed Mar 26 19:54:54 2014 mstenber
# Edit time:     233 min
#
"""

(Python) Coroutine-based Testing Framework.

Basic idea:

- using a set of step sequences, execution of which are synchronous,
    define a set of tests and test suites.

- within step, have wildly asynchronous behavior: monitor log files,
    execute commands on VMs

(In principle, could have reused e.g. unittest or nose; but in
practise, the amount of glue code is small, and the asyncio magic
involved is the hairy part).

The datastructures are defined to be highly composable, with access to
the shared 'state' object. The test runner is just responsible for
firing up the root level objects, and ultimately execution is up to
set of test steps.

"""

import time
import asyncio
import concurrent.futures
import subprocess
from asyncio.subprocess import PIPE

import logging
_logger = logging.getLogger('cotest')
_debug = _logger.debug
_info = _logger.info

@asyncio.coroutine
def _async_run(fun, *args):
    p = yield from fun(*args, stdout=PIPE, stderr=PIPE)
    try:
        stdout, stderr = yield from p.communicate()
    except:
        _debug('communicate exception')
        try:
            p.kill()
            yield from p.wait()
        except:
            _debug('.. kill failed')
            pass
        raise
    exitcode = yield from p.wait()
    return (exitcode, stdout, stderr)

@asyncio.coroutine
def async_system(cmd):
    _debug('async_system %s' % cmd)
    return _async_run(asyncio.create_subprocess_shell, cmd)


# async_system seems to have issues.. so provide replacement that just
# returns (fake) empty output
def sync_system(cmd, timeout):
    assert timeout
    _debug('!!! sync_system %s' % cmd)
    cmd = cmd + '2>/dev/null >/dev/null'
    try:
        return subprocess.call(cmd, shell=True, timeout=timeout), b'', b''
    except subprocess.TimeoutExpired:
        return -1, b'', b''

@asyncio.coroutine
def async_exec(*args):
    _debug('async_exec %s' % args)
    return _async_run(asyncio.create_subprocess_exec, *args)

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

class Runnable:
    def run():
        raise NotImplementedError

class StepBase(Named, Runnable):
    def __init__(self,
                 *,
                 name=None,
                 timeout=None,
                 exceptionIsFailure=False):
        Named.__init__(self, name)
        self.timeout = timeout
        self.exceptionIsFailure = exceptionIsFailure
    def doneErrors(self, l):
        for o in l:
            _debug('checking errors in %s' % repr(o))
            if self.exceptionIsFailure:
                e = o.exception()
                if e:
                    _info('exception %s occurred in %s' % (repr(e),
                                                           repr(o)))
                    return True
        return False

class Step(StepBase):
    def __init__(self,
                 fun,
                 *,
                 failIf=None,
                 **kwargs):
        StepBase.__init__(self, **kwargs)
        self.fun = fun
        self.failIf = failIf
    def run(self, state=None):
        _debug('%s run()' % repr(self))
        if state is None: state = {}
        r = yield from self.runAsync(state, self.fun, self.failIf)
        if r != 0:
            _info('%s failed: %s' % (repr(self), repr(self.fun)))
            return False
        return True
    def runAsync(self, state, *args):
        assert args, 'must have at least one job'
        def _convert(x):
            r = x(state)
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
        if self.doneErrors(done):
            return
        for i, o in enumerate(l):
            _debug('considering %s' % repr(o))
            if o and o in done:
                if o.result():
                    return i
                return
        return

def _toStep(x):
    assert x
    if not isinstance(x, StepBase):
        x = Step(x)
    return x

class NotStep(StepBase):
    def __init__(self, step, **kwargs):
        StepBase.__init__(self, **kwargs)
        self.step = _toStep(step)
    def run(self, state=None):
        if state is None: state = {}
        r = yield from self.step.run(state)
        return not r

class RepeatStep(StepBase):
    def __init__(self, step, *, wait=None, timeout=None, times=None, **kwargs):
        StepBase.__init__(self, **kwargs)
        assert timeout or times
        self.step = _toStep(step)
        self.times = times
        self.timeout = timeout
        self.wait = wait
    def run(self, state=None):
        if state is None: state = {}
        i = 0
        if self.timeout:
            st = time.monotonic()
            et = st + self.timeout
        r = False
        ot = self.step.timeout
        while (self.times is None or i < self.times) and (self.timeout is None or time.monotonic() <= et):
            if self.timeout:
                self.step.timeout = et - time.monotonic()
                if self.step.timeout <= 0:
                    break
            r = yield from self.step.run(state)
            if r:
                r = True
                break
            if self.wait:
                yield from asyncio.sleep(self.wait)
            i += 1
        self.step.timeout = ot
        return r

# Abstract base class for multiple step bandling
# NOTE: This does not support synchronous steps!
class MultiStepBase(StepBase):
    def __init__(self, *steps, **kwargs):
        StepBase.__init__(self, **kwargs)
        assert len(steps) >= 1, 'multistep with 0 arguments is not useful'
        self.steps = map(_toStep, steps)
    def run(self, state=None):
        _debug('%s run()' % repr(self))
        if state is None: state = {}
        def _convert(x):
            r = x.run(state)
            _debug('starting %s => %s' % (repr(x), repr(r)))
            assert r and asyncio.iscoroutine(r)
            return asyncio.Task(r)
        l = map(_convert, self.steps)
        return self.waitResult(l)
    def waitResult(self, l):
        # Child responsibility
        raise NotImplementedError

class OrStep(MultiStepBase):
    def waitResult(self, l):
        # This has bit more .. magical.. handling
        l = list(l)
        nto = None
        to = self.timeout
        if to:
            st = time.monotonic()
        while l:
            if to:
                nto = to - (time.monotonic() - st)
                if nto <= 0:
                    return
            done, pending = yield from asyncio.wait(l, timeout=nto,
                                                    return_when=concurrent.futures.FIRST_COMPLETED)
            _debug('%s asyncio.wait got %s,%s' % (repr(self), done, pending))
            if not done:
                _debug('%s failed due to timeout')
                return False
            if self.doneErrors(done):
                return False
            for o in done:
                if o.result():
                    return True
                l.remove(o)
        # If we run out of list, we're failure
        return

class AndStep(MultiStepBase):
    def waitResult(self, l):
        done, pending = yield from asyncio.wait(l, timeout=self.timeout)
        _debug('%s asyncio.wait got %s,%s' % (repr(self), done, pending))
        if pending:
            _debug('%s failed due to pending %s' % (repr(self), repr(pending)))
            return False
        if self.doneErrors(done):
            return False
        assert done
        failed = list(filter(lambda x:not x.result(), done))
        return not failed


class StepSequence(Named, Runnable):
    def __init__(self, steps, *, name=None, stopFail=True):
        Named.__init__(self, name)
        self.steps = steps
        self.stopFail = stopFail
    def run(self, state=None):
        if state is None: state = {}
        r = True
        for i, o in enumerate(self.steps):
            o = _toStep(o)
            _debug('%s running step #%d: %s' % (repr(self),i,repr(o)))
            cr = yield from o.run(state)
            if not cr:
                _info("%s step #%d failed" % (repr(self), i))
                if self.stopFail:
                    return False
                r = False
        return r

class TestCase(Named, Runnable):
    def __init__(self, main, *, name=None, setup=None, tearDown=None):
        Named.__init__(self, name)
        self.main = main
        self.setup = setup
        self.tearDown = tearDown
    def run(self, state=None):
        if state is None: state = {}
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
            x = StepSequence([x])
        r = yield from x.run(state)
        return r

# TestSuite == StepSequence. Brilliant!
def run(*args):
    loop = asyncio.get_event_loop()
    r = True
    for i, arg in enumerate(args):
        _debug('run() running #%d:%s' % (i, repr(arg)))
        if isinstance(arg, Runnable):
            arg = arg.run
        t = asyncio.async(arg())
        loop.run_until_complete(t)
        if not t.result():
            r = False
    _debug('run() result: %s' % repr(r))
    return r

if __name__ == '__main__':
    pass
