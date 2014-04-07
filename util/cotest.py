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
# Last modified: Mon Apr  7 14:07:06 2014 mstenber
# Edit time:     282 min
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

class StepBase(Named):
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
    def run(self, state=None, *, depth=0):
        raise NotImplementedError

class Step(StepBase):
    def __init__(self,
                 fun,
                 *,
                 failIf=None,
                 **kwargs):
        StepBase.__init__(self, **kwargs)
        self.fun = fun
        self.failIf = failIf
    def run(self, state=None, *, depth=0):
        _debug('[%d] %s run()' % (depth, repr(self)))
        if state is None: state = {}
        r = yield from self.runAsync(state, self.fun, self.failIf)
        if r != 0:
            _info('[%d] %s failed: %s' % (depth, repr(self), repr(self.fun)))
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

# noneOk=True case is mostly usable as input to StepSequence..
def _toStep(x, noneOk=False):
    if x is None and noneOk:
        return
    assert x
    if isinstance(x, StepBase):
        return x
    try:
        iter(x)
        return StepSequence(x)
    except:
        return Step(x)

class NotStep(StepBase):
    def __init__(self, step, **kwargs):
        StepBase.__init__(self, **kwargs)
        self.step = _toStep(step)
    def run(self, state=None, *, depth=0):
        if state is None: state = {}
        r = yield from self.step.run(state, depth=depth+1)
        return not r

class RepeatStep(StepBase):
    def __init__(self, step, *, wait=None, timeout=None, times=None, **kwargs):
        StepBase.__init__(self, **kwargs)
        self.step = _toStep(step)
        self.times = times
        self.timeout = timeout
        self.wait = wait
    def run(self, state=None, *, depth=0):
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
            r = yield from self.step.run(state, depth=depth+1)
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
    def run(self, state=None, *, depth=0):
        _debug('%s run()' % repr(self))
        if state is None: state = {}
        def _convert(x):
            r = x.run(state, depth=depth+1)
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


class StepSequence(StepBase):
    def __init__(self, steps, *, stopFail=True, **kwargs):
        StepBase.__init__(self, **kwargs)
        try:
            iter(steps)
        except:
            steps = [steps]
        steps = filter(None, steps)
        self.steps = steps
        self.stopFail = stopFail
    def run(self, state=None, *, depth=0):
        if state is None: state = {}
        r = True
        for i, o in enumerate(self.steps):
            if not isinstance(o, StepBase):
                o = _toStep(o)
            _debug('[%d] %s running step #%d: %s' % (depth,
                                                     repr(self), i, repr(o)))
            cr = yield from o.run(state, depth=depth+1)
            if not cr:
                _info("[%d] %s step #%d failed" % (depth, repr(self), i))
                if self.stopFail:
                    return False
                r = False
        return r

class TestCase(StepSequence):
    setup = None
    tearDown = None
    tearDownAlways = None
    def __init__(self, main, *,
                 setup=None, tearDown=None, tearDownAlways=True, **kwargs):
        if setup is None:
            setup = self.setup
        if tearDown is None:
            tearDown = self.tearDown
        if tearDownAlways is None:
            tearDownAlways = self.tearDownAlways
        setup = _toStep(setup, True)
        main = _toStep(main, True)
        tearDown = _toStep(tearDown, True)
        if tearDownAlways:
            StepSequence.__init__(self,
                                  [StepSequence([setup, main]), tearDown],
                                  stopFail=False,
                                  **kwargs)
        else:
            StepSequence.__init__(self,
                                  [setup, main, tearDown],
                                  **kwargs)

class TestSuite(StepSequence):
    def __init__(self, cases, **kwargs):
        return StepSequence.__init__(self, cases, stopFail=False, **kwargs)

def run(*args):
    loop = asyncio.get_event_loop()
    r = True
    for i, arg in enumerate(args):
        _debug('run() running #%d:%s' % (i, repr(arg)))
        if isinstance(arg, StepBase):
            arg = arg.run
        t = asyncio.async(arg())
        loop.run_until_complete(t)
        if not t.result():
            r = False
    _debug('run() result: %s' % repr(r))
    return r

if __name__ == '__main__':
    pass
