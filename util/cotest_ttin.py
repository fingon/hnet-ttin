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
# Last modified: Wed Mar 26 15:21:41 2014 mstenber
# Edit time:     141 min
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
def _killTopology():
    cmd = 'vclean --clean-all'
    rc, *x = yield from cotest.async_system(cmd)
    return rc == 0

@asyncio.coroutine
def _nodeShell(node, cmd):
    s = "uml_mconsole %s exec '%s'" % (node, cmd)
    (rc, stdout, stderr) = yield from cotest.async_system(s)
    if stdout[:3] != b'OK ':
        _info('_nodeShell returned non-ok for %s' % node)
        return (-1, b'', b'')
    return (rc, stdout[3:], stderr)

def startTopology(topology, routerTemplate, *, ispTemplate=None, timeout=60):
    @asyncio.coroutine
    def _run(state):
        # Check we're inside ttin main directory
        f = open('util/cotest.py')
        f.close()
        args = []
        if routerTemplate:
            args.append('--replace-template')
            args.append('bird=%s' % routerTemplate)
        if ispTemplate:
            args.append('--replace-template')
            args.append('isp4-6=%s' % ispTemplate)
        args.append(topology)
        args = ' '.join(args)
        r = yield from _killTopology()

        rc, *x = yield from cotest.async_system('rm -rf lab/%s' % topology)
        if rc:
            _info('rm topology failed with exit code %d' % rc)
            return

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
        f = open('lab/%s/lab.conf' % topology)
        for line in f:
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
        f.close()
        cmd = '(cd lab/%s && lstart -p123 < /dev/null)' % topology
        rc, stdout, stderr = cotest.sync_system(cmd, timeout)
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

def nodeHasPrefix(node, prefix, *, timeout=3):
    def _run(state):
        rc, stdout, stderr = yield from _nodeShell(node, 'ifconfig | grep -q "%s" && echo found' % prefix)
        return rc == 0 and 'found' in stdout.decode()
    return cotest.Step(_run,
                       name='@%s:check for %s' % (node, prefix),
                       timeout=timeout)

IFCONFIG_V4_PREFIX='inet addr:'
IFCONFIG_V6_PREFIX='inet6 addr: '

def nodeHasPrefix4(node, prefix, **kwargs):
    return nodeHasPrefix(node, IFCONFIG_V4_PREFIX + prefix, **kwargs)

def nodeHasPrefix6(node, prefix, **kwargs):
    return nodeHasPrefix(node, IFCONFIG_V6_PREFIX + prefix, **kwargs)

def waitRouterPrefix(prefix, *, timeout=120):
    def _run(state):
        # For every router in the configuration, make sure the prefix is visible

        def _convert(node):
            return cotest.RepeatStep(nodeHasPrefix(node, prefix),
                                     wait=1, timeout=timeout)
        l = list(map(_convert, state['routers']))
        assert len(l) >= 2
        s = cotest.AndStep(*l)
        r = yield from s.run(state)
        return r
    return cotest.Step(_run, name='wait prefix %s' % prefix)

def waitRouterPrefix4(prefix, **kwargs):
    return waitRouterPrefix(IFCONFIG_V4_PREFIX + prefix, **kwargs)

def waitRouterPrefix6(prefix, **kwargs):
    return waitRouterPrefix(IFCONFIG_V6_PREFIX + prefix, **kwargs)

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
        r = yield from _killTopology()
        return r
    return cotest.Step(_run, name='killTopology', timeout=timeout)

# Built-in unit tests that just run through the templates once
base_4_test = [
    waitRouterPrefix4('10.'),
    cotest.NotStep(nodeHasPrefix4('client', '10.')),
    cotest.NotStep(nodePing4('client', 'h-server')),
    nodeRun('client', 'dhclient eth0'),
    nodeHasPrefix4('client', '10.'),
    cotest.RepeatStep(nodePing4('client', 'h-server'), wait=1, timeout=5),
    nodePing4('client', 'server.v4.lab.example.com'),
]

base_6_local_test = [
    # May need to wait for routing to settle here => need long timeouts
    cotest.RepeatStep(nodePing6('client', 'bird3.eth0.bird3.home'),
                      wait=1, timeout=60),
    cotest.RepeatStep(nodePing6('client', 'cpe.eth0.cpe.home'),
                      wait=1, timeout=60),
    ]

base_6_test = [
    waitRouterPrefix6('200'),
    nodeHasPrefix6('client', '200'),
    cotest.RepeatStep(nodePing6('client', 'h-server'), wait=1, timeout=30),
    nodePing6('client', 'server.v6.lab.example.com'),
    ] + base_6_local_test

base_test = [
    startTopology('bird7', 'obird'),
    ] + base_6_test + base_4_test


if __name__ == '__main__':
    import logging
    #logging.basicConfig(level=logging.INFO)
    logging.basicConfig(level=logging.DEBUG)
    al = logging.getLogger('asyncio')
    al.setLevel(logging.CRITICAL)
    tc = cotest.TestCase(base_test)
    cotest.run(tc)

