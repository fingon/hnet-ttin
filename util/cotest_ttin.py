#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: cotest_ttin.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Tue Mar 25 10:39:18 2014 mstenber
# Last modified: Tue Mar 25 14:50:58 2014 mstenber
# Edit time:     79 min
#
"""

ttin topology play utility functions for cotest

Basic design:

- keep track of 'set up' things in the state object

- clean them in tearDown

- do things as synchronously as possible (e.g. topology setup) but
  don't hesitate to be asynchronous when it's warranted (keeping track
  of multiple logfiles using bunch of tail -f's, for example)

"""

import cotest
import asyncio
import re

import logging
_logger = logging.getLogger('cotest_ttin')
_debug = _logger.debug
_info = _logger.info

_template_re = re.compile('^# (\S+)\[template\] = (\S+)$').match

KEY_TOPOLOGY='topology'

@asyncio.coroutine
def _nodeShell(node, cmd):
    s = "uml_mconsole %s exec '%s'" % (node, cmd)
    r = yield from cotest.async_system(s)
    return r

def startTopology(topology, routerTemplate, *, ispTemplate=None, timeout=120):
    @asyncio.coroutine
    def _run(state):
        # Check we're inside ttin main directory
        assert open('util/cotest.py')
        args = []
        if routerTemplate:
            args.append('--replace-template')
            args.append('bird=%s' % routerTemplate)
        if ispTemplate:
            args.append('--replace-template')
            args.append('isp=%s' % ispTemplate)
        args.append(topology)
        args = ' '.join(args)
        rc, *x = yield from cotest.async_system('python util/case2lab.py %s' % args)
        if rc:
            _info('case2lab failed with exit code %d' % rc)
            return
        nd = {}
        state['nodes'] = nd
        rd = {}
        state['routers'] = rd
        cd = {}
        state['clients'] = cd
        isd = {}
        state['isps'] = isd
        for line in open('lab/%s/lab.conf' % topology):
            m = _template_re(line)
            if m is None: continue
            (node, template) = m.groups()
            nd[node] = {'template': template}
            if template == routerTemplate:
                rd[node] = {}
            if 'isp' in node:
                isd[node] = {}
            if 'client' in node:
                cd[node] = {}
        cmd = '(cd lab/%s && lstart -p123 < /dev/null)' % topology
        rc, stdout, stderr = cotest.sync_system(cmd)
        # wish this wasn't broken
        #rc, stdout, stderr = yield from cotest.async_system(cmd)
        if rc:
            _info('lstart failed with exit code %d: %s' % (rc, stderr))
            return
        if 'already running' in stderr.decode():
            _info('lstart succeeded but topo was running before')
            return
        state[KEY_TOPOLOGY] = topology
        return True
    n = 'startTopology %s/%s/%s' % (topology, routerTemplate, ispTemplate)
    return cotest.Step(_run, name=n, timeout=timeout)

def nodeRun(node, cmd):
    def _run(state):
        rc, *x = yield from _nodeShell(node, cmd)
        return rc == 0
    return cotest.Step(_run, name='@%s:%s' % (node, cmd))

def nodePing4(node, remote):
    def _run(state):
        rc, stdout, stderr = yield from _nodeShell(node, 'ping -c 1 %s' % remote)
        return rc == 0 and ' bytes from ' in stdout.decode()
    return cotest.Step(_run, name='@%s:ping %s' % (node, remote))

def nodePing6(node, remote):
    def _run(state):
        rc, stdout, stderr = yield from _nodeShell(node, 'ping6 -c 1 %s' % remote)
        return rc == 0 and ' bytes from ' in stdout.decode()
    return cotest.Step(_run, name='@%s:ping6 %s' % (node, remote))

def killTopology(timeout=60):
    @asyncio.coroutine
    def _run(state):
        if not KEY_TOPOLOGY in state:
            _debug('topology not running, not killing it')
            return True
        del state[KEY_TOPOLOGY]
        del state['clients']
        del state['routers']
        del state['isps']
        del state['nodes']
        cmd = 'vclean --clean-all'
        rc, *x = yield from cotest.async_system(cmd)
        #rc, *x = cotest.sync_system(cmd)
        return rc == 0
    return cotest.Step(_run, name='killTopology', timeout=timeout)

if __name__ == '__main__':
    import logging
    #logging.basicConfig(level=logging.INFO)
    logging.basicConfig(level=logging.DEBUG)
    # Built-in unit tests that just run through the templates once
    l = [
        startTopology('bird7', 'obird'),
        cotest.RepeatStep(nodePing6('client', 'h-server'),
                          wait=5, timeout=120),
        cotest.NotStep(nodePing4('client', 'h-server')),
        nodeRun('client', 'dhclient eth0'),
        cotest.RepeatStep(nodePing4('client', 'h-server'),
                          wait=5, timeout=60),
        killTopology(),
        ]
    tc = cotest.TestCase(l)
    cotest.run(tc)

