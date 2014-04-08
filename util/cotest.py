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
# Last modified: Tue Apr  8 15:09:58 2014 mstenber
# Edit time:     338 min
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

The datastructures that the testcases and their individual test steps
consist of are immutable and therefore highly composable, with access
to the shared 'state' object. The test runner is just responsible for
firing up the root level objects, and ultimately execution is up to
set of test steps.

"""

import time
import asyncio
import concurrent.futures
import subprocess
from asyncio.subprocess import PIPE
import logging
import copy

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
    def run(self, state=None):
        """ This routine is wrapper which is responsible for making
        sure that a) consistent state is available to subcalls, b) it
        has depth, and c) timeout information about when the run ends
        if any; the most recent one being in 'ets'[-1]."""
        if state is None:
            state = {'ets': []}
            _debug(' initializing fresh state')
        elif type(state) != type({}):
            state = {'ets': [], 'wstate': state}
            _debug(' wrapping state %s' % state)
        depth = state.get('depth', 0)
        ours = False
        if self.timeout:
            et = time.monotonic() + self.timeout
            ets = state['ets']
            if not ets or ets[-1] > et:
                ets.append(et)
                ours = True
        try:
            state['depth'] = depth + 1
            _debug('[%d] %s run()' % (depth, repr(self)))
            r = yield from self.reallyRun(state)
            if not r:
                _info('[%d] %s run() failed' % (depth, repr(self)))
        finally:
            state['depth'] = depth
            if ours:
                del ets[-1]
        return r
    def reallyRun(self, state):
        raise NotImplementedError

def _state_et(state):
    ets = state['ets']
    timeout = None
    if ets:
        return ets[-1]

def _state_timeout(state):
    et = _state_et(state)
    if et:
        return et - time.monotonic()

class Step(StepBase):
    def __init__(self,
                 fun,
                 *,
                 failIf=None,
                 **kwargs):
        StepBase.__init__(self, **kwargs)
        self.fun = fun
        self.failIf = failIf
    def reallyRun(self, state):
        r = yield from self.runAsync(state, self.fun, self.failIf)
        if r != 0:
            return False
        return True
    def runAsync(self, state, *args):
        assert args, 'must have at least one job'
        def _convert(x):
            wstate = state.get('wstate', state)
            r = x(wstate)
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
        timeout = _state_timeout(state)
        done, pending = yield from asyncio.wait(l, timeout=timeout,
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
    if isinstance(x, StepBase):
        return x
    try:
        iter(x)
        return StepSequence(x)
    except:
        return Step(x)

def _toStepOrNone(x):
    if x is None:
        return None
    return _toStep(x)

class NotStep(StepBase):
    def __init__(self, step, **kwargs):
        StepBase.__init__(self, **kwargs)
        self.step = _toStep(step)
    def reallyRun(self, state):
        r = yield from self.step.run(state)
        return not r

class RepeatStep(StepBase):
    def __init__(self, step, *, wait=None, timeout=None, times=None, **kwargs):
        StepBase.__init__(self, timeout=timeout, **kwargs)
        self.step = _toStep(step)
        self.times = times
        self.wait = wait
    def reallyRun(self, state):
        i = 0
        et = _state_et(state)
        r = False
        while (self.times is None or i < self.times) and (not et or time.monotonic() <= et):
            r = yield from self.step.run(state)
            if r:
                r = True
                break
            if self.wait:
                yield from asyncio.sleep(self.wait)
            i += 1
        return r

# Abstract base class for multiple step bandling
# NOTE: This does not support synchronous steps!
class MultiStepBase(StepBase):
    def __init__(self, *steps, **kwargs):
        StepBase.__init__(self, **kwargs)
        assert len(steps) >= 1, 'multistep with 0 arguments is not useful'
        self.steps = map(_toStep, steps)
    def reallyRun(self, state):
        def _convert(x):
            lstate = copy.deepcopy(state)
            r = x.run(lstate)
            _debug('starting %s => %s' % (repr(x), repr(r)))
            assert r and asyncio.iscoroutine(r)
            return asyncio.Task(r)
        l = map(_convert, self.steps)
        return self.waitResult(state, l)
    def waitResult(self, l):
        # Child responsibility
        raise NotImplementedError

class OrStep(MultiStepBase):
    def waitResult(self, state, l):
        # This has bit more .. magical.. handling
        l = list(l)
        et = _state_et(state)
        nto = None
        while l:
            if et:
                nto = et - time.monotonic()
                if nto <= 0:
                    return
            done, pending = yield from asyncio.wait(l, timeout=nto,
                                                    return_when=concurrent.futures.FIRST_COMPLETED)
            _debug('%s asyncio.wait got %s,%s' % (repr(self), done, pending))
            if not done:
                _debug('timeout')
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
    def waitResult(self, state, l):
        to = _state_timeout(state)
        done, pending = yield from asyncio.wait(l, timeout=to)
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
    def reallyRun(self, state):
        depth = state['depth']
        r = True
        for i, o in enumerate(self.steps):
            o = _toStep(o)
            _debug('[%d] %s running step #%d: %s' % (depth,
                                                     repr(self), i, repr(o)))
            cr = yield from o.run(state)
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
        setup = _toStepOrNone(setup)
        main = _toStepOrNone(main)
        tearDown = _toStepOrNone(tearDown)
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
