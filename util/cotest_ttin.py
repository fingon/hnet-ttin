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
# Last modified: Tue Apr 29 11:13:47 2014 mstenber
# Edit time:     400 min
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
import os, os.path

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

class MConsoleDeadException(Exception):
    pass

class NodeDeadException(Exception):
    pass

class ProcessCrashedException(Exception):
    pass

@asyncio.coroutine
def _node(node, cmd):
    s = "uml_mconsole %s %s" % (node, cmd)
    (rc, stdout, stderr) = yield from cotest.async_system(s)
    if stdout[:3] != b'OK ':
        _info('_nodeExec returned non-ok for %s' % node)
        raise MConsoleDeadException(node)
    return (rc, stdout[3:], stderr)

@asyncio.coroutine
def _nodeExec(node, cmd):
    return _node(node, "exec '%s'" % cmd)

def nodeStop(node):
    @asyncio.coroutine
    def _run(state):
        if 'stopped' in state['nodes'][node]:
            return True
        rc, *x = yield from _node(node, 'stop')
        if rc == 0:
            state['nodes'][node]['stopped'] = True
            return True
    return cotest.Step(_run, name='stop %s' % node)

def nodeGo(node):
    @asyncio.coroutine
    def _run(state):
        if 'stopped' not in state['nodes'][node]:
            return True
        rc, *x = yield from _node(node, 'go')
        if rc == 0:
            del state['nodes'][node]['stopped']
            return True

    return cotest.Step(_run, name='go %s' % node)

# Allow for fail or two
def startTopology(topology, routerTemplate, *, ispTemplate=None, timeout=300, originalRouterTemplate="router"):
    @asyncio.coroutine
    def _run(state):
        # Check we're inside ttin main directory
        with open('util/cotest.py') as f:
            pass
        args = []
        if routerTemplate:
            args.append('--replace-template')
            args.append('%s=%s' % (originalRouterTemplate, routerTemplate))
        if ispTemplate:
            args.append('--replace-template')
            args.append('isp4-6=%s' % ispTemplate)
        args.append(topology)
        args = ' '.join(args)
        r = yield from _killTopology()

        #cmd = 'rm -rf lab/%s' % topology
        cmd = 'rm -rf lab'

        rc, *x = yield from cotest.async_system(cmd)
        if rc:
            _info('rm topology failed with exit code %d' % rc)
            return

        rc, *x = yield from cotest.async_system('python util/case2lab.py %s' % args)
        if rc:
            _info('case2lab failed with exit code %d' % rc)
            return
        nd = {}
        state['topology'] = topology
        state['nodes'] = nd
        rd = {}
        state['routers'] = rd
        cd = {}
        state['clients'] = cd
        isd = {}
        state['isps'] = isd
        with open('lab/%s/lab.conf' % topology) as f:
            home = os.environ['HOME']
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
                rc, *x = yield from cotest.async_system('rm -rf %s' % os.path.join(home, '.netkit', 'mconsole', node))
                if rc:
                    _info('rm mconsole failed with exit code %d' % rc)
                    return
        assert rd, 'have to have routers present'
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
        s = [routersReady(), topologyLives()]
        rs = cotest.RepeatStep(s, wait=5)
        r = yield from rs.run(state)
        return r
    n = 'startTopology %s/%s/%s' % (topology, routerTemplate, ispTemplate)
    return cotest.RepeatStep(cotest.Step(_run, name=n, timeout=timeout,
                                         exceptionIsFailure=True),
                             wait=1,
                             timeout=timeout)

def routerReady(router):
    n = 'router %s ready' % router
    def _run(state):
        fn = 'lab/%s/logs/%s/status' % (state['topology'], router)
        try:
            with open(fn) as f:
                d = f.read()
            return 'done' in d
        except IOError:
            return
    return cotest.Step(_run, name=n)

crash_re = re.compile('\s(\S+)\[\d+\]: segfault').search

def routerNoCrashes(router):
    n = 'no crashes at router %s' % router
    def _run(state):
        fn = 'lab/%s/logs/%s/syslog.log' % (state['topology'], router)
        try:
            with open(fn) as f:
                for line in f:
                    m = crash_re(line)
                    if m is not None:
                        raise ProcessCrashedException(m.group(1))
        except IOError:
            return True
        return True
    return cotest.Step(_run, name=n)

def _runningRouterNames(state):
    return filter(lambda x:'stopped' not in state['nodes'][x],
                  state['routers'].keys())

def _forAllRouters(f, n):
    def _run(state):
        l = map(f, _runningRouterNames(state))
        s = cotest.AndStep(*l, name=n)
        r = yield from s.run(state)
        return r
    return cotest.Step(_run, name=n)


def routersNoCrashes():
    return _forAllRouters(routerNoCrashes, 'routers did not crash')

def routersReady():
    return _forAllRouters(routerReady, 'routers ready')

def nodeLives(node):
    def _run(state):
        cmd = 'ps ax | grep -v grep | grep -q "umid=%s" && echo found' % node
        rc, stdout, stderr = yield from cotest.async_system(cmd)
        if rc != 0 or b'found' not in stdout:
            raise NodeDeadException(node)
        try:
            rc, r, err = yield from _nodeExec(node, 'echo foo')
        except MConsoleDeadException:
            _debug('node %s not ok - mconsole died' % node)
            return
        if not (rc == 0 and b'foo' in r):
            _debug('node %s not ok - %d' % (node, rc))
            return False
        return True
    return cotest.Step(_run, name='%s lives' % node)

def topologyLives():
    n = 'topology lives'
    def _run(state):
        l = map(nodeLives, state['nodes'].keys())
        s = cotest.AndStep(*l, name=n)
        r = yield from s.run(state)
        return r
    return cotest.Step(_run, name=n)

def nodeRun(node, cmd):
    def _run(state):
        rc, *x = yield from _nodeExec(node, cmd)
        return rc == 0
    return cotest.Step(_run, name='@%s:%s' % (node, cmd))

def nodePing4(node, remote):
    def _run(state):
        rc, stdout, stderr = yield from _nodeExec(node, 'ping -c 1 %s' % remote)
        return rc == 0 and ' bytes from ' in stdout.decode()
    return cotest.Step(_run, name='@%s:ping %s' % (node, remote))

def nodePing6(node, remote, args='', source='', c=1, n=True):
    if source:
        args = args + ' -I %s' % source
    if n:
        args = args + ' -n'
    if c:
        args = args + ' -c %d' % c
    def _run(state):
        rc, stdout, stderr = yield from _nodeExec(node, 'ping6 %s %s' % (args, remote))
        return rc == 0 and ' bytes from ' in stdout.decode()
    return cotest.Step(_run, name='@%s:ping6 %s' % (node, remote))

def nodeTraceroute6Contains(node, remote, data):
    # In principle this should work; however, traceroute6 does
    # something stupid with tty and it's not compatible with mconsole
    # exec..
    raise NotImplementedError
    def _run(state):
        rc, r, stderr = yield from _nodeExec(node, 'traceroute6 %s' % remote)
        if rc:
            return
        if not data in r:
            _debug('missing %s from %s' % (data.decode(), r.decode()))
            return
        return True
    return cotest.Step(_run, name='@%s:traceroute6 %s has %s' % (node, remote, data))

CMD_IP4_ADDRS='ip -4 addr | grep inet'
CMD_IP6_ADDRS='ip -6 addr show scope global | grep -v deprecated | grep inet6'

IP_V4_PREFIX='inet '
IP_V6_PREFIX='inet6 '

def _nodeHasPrefix(node, cmd, prefix, *, timeout=3):
    def _run(state):
        rc, stdout, stderr = yield from _nodeExec(node, '%s | grep -q "%s" && echo found' % (cmd, prefix))
        return rc == 0 and b'found' in stdout
    return cotest.Step(_run,
                       name='@%s:check for %s' % (node, prefix),
                       timeout=timeout, exceptionIsFailure=True)

def nodeHasPrefix4(node, prefix, **kwargs):
    return _nodeHasPrefix(node, CMD_IP4_ADDRS, IP_V4_PREFIX + prefix, **kwargs)

def nodeHasPrefix6(node, prefix, **kwargs):
    return _nodeHasPrefix(node, CMD_IP6_ADDRS, IP_V6_PREFIX + prefix, **kwargs)

def updateNodeAddresses6(node, *, minimum=1, maximum=None, timeout=5, exclude=[]):
    def _run(state):
        rc, stdout, stderr = yield from _nodeExec(node, CMD_IP6_ADDRS)
        rl = []
        state['nodes'][node]['addrs'] = rl
        for line in stdout.decode().split('\n'):
            line = line.strip()
            _debug(' got %s' % line)
            l = line.split(' ')
            if len(l) < 2:
                continue
            addr = l[1]
            assert '/' in addr
            addr = addr.split('/')[0]
            found = False
            for e in exclude:
                if addr.startswith(e):
                    found = True
                    break
            if not found:
                rl.append(addr)
        if minimum and len(rl) < minimum:
            return
        if maximum and len(rl) > maximum:
            return
        return True
    return cotest.Step(_run,
                       name='@%s get IPv6 addresses' % node,
                       timeout=timeout)

def nodePingFromAll6(node, remote, **kwargs):
    def _run(state):
        def _convert(a):
            return nodePing6(node, remote, source=a, **kwargs)
        l = map(_convert, state['nodes'][node]['addrs'])
        s = cotest.AndStep(*l)
        r = yield from s.run(state)
        return r
    return cotest.Step(_run, name='@%s:all-ping6 %s' % (node, remote))

def nodePingToAll6(node, remote, **kwargs):
    def _run(state):
        def _convert(a):
            return nodePing6(node, a, **kwargs)
        l = map(_convert, state['nodes'][remote]['addrs'])
        s = cotest.AndStep(*l)
        r = yield from s.run(state)
        return r
    return cotest.Step(_run, name='@%s:all-ping6 %s' % (node, remote))

def nodeInterfaceFirewallZoneIs(node, interface, zone):
    def _run(state):
        cmd = 'ifstatus %s | grep "\\"zone\\": " | cut -d ":" -f 2' % interface
        rc, r, stderr = yield from _nodeExec(node, cmd)
        if rc:
            return
        r = r.decode().strip()
        return r == '"%s"' % zone
    return cotest.Step(_run, name='@%s:fwzone %s=%s' % (node, interface, zone))

def _waitRouterPrefix(cmd, prefix, *, wait=1, timeout=60):
    n = 'wait prefix %s' % prefix
    def _run(state):
        # For every router in the configuration, make sure the prefix is visible

        def _convert(node):
            return cotest.RepeatStep(_nodeHasPrefix(node, cmd, prefix),
                                     wait=wait, timeout=timeout)
        l = map(_convert, _runningRouterNames(state))
        s = cotest.AndStep(*l, name=n)
        r = yield from s.run(state)
        return r
    return cotest.Step(_run, name=n)

def waitRouterPrefix4(prefix, **kwargs):
    return _waitRouterPrefix(CMD_IP4_ADDRS, IP_V4_PREFIX + prefix, **kwargs)

def waitRouterPrefix6(prefix, **kwargs):
    return _waitRouterPrefix(CMD_IP6_ADDRS, IP_V6_PREFIX + prefix, **kwargs)

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

def sleep(timeout):
    @asyncio.coroutine
    def _run(state):
        yield from asyncio.sleep(timeout)
        return True
    return cotest.Step(_run, name='sleep %d' % timeout)

# How long can it take for routing to settle? Given how slowly UML
# works, 60 seconds might be pushing it in the bigger topology.. :p
#
TIMEOUT_INITIAL=60

# This is acceptable timeout after the 'initial' case, when we already
# assume we have e.g. all prefixes visible on the network
TIMEOUT=60

# Built-in unit tests that just run through the templates once

base_4_setup_test = [
    waitRouterPrefix4('10.', timeout=TIMEOUT_INITIAL),
    #cotest.NotStep(nodeHasPrefix4('client', '10.')), # in nested pd, 192.*
    cotest.NotStep(nodePing4('client', 'h-server')),
    nodeRun('client', 'dhclient eth0'),
    ]

base_4_remote_test = [
    # this is never first -> no need for TIMEOUT_INITIALs
    #nodeHasPrefix4('client', '10.'), # in nested pd, we do 192.*
    # 30 seconds =~ time for routing to settle
    cotest.RepeatStep(nodePing4('client', 'h-server'), wait=1, timeout=TIMEOUT),
    cotest.RepeatStep(nodePing4('client', 'server.v4.lab.example.com'), wait=1, timeout=TIMEOUT),
    ]

base_4_local_test = [
    # Service discovery
    cotest.RepeatStep(nodePing4('client', 'cpe.eth0.cpe.home'),
                      wait=1, timeout=TIMEOUT_INITIAL),
    # If it's not first-hop, availability of cpe doesn't imply ir3
    cotest.RepeatStep(nodePing4('client', 'ir3.eth0.ir3.home'),
                      wait=1, timeout=TIMEOUT),

    ]

base_4_test = base_4_setup_test + base_4_remote_test + base_4_local_test

# Just ping
base_6_local_ip_step = cotest.RepeatStep([updateNodeAddresses6('cpe', exclude=['fd']), nodePingToAll6('client', 'cpe')], wait=1, timeout=TIMEOUT)

# Service discovery
base_6_local_sd_test = [
    cotest.RepeatStep(nodePing6('client', 'cpe.eth0.cpe.home'),
                      wait=1, timeout=TIMEOUT_INITIAL),
    # If it's not first-hop, availability of cpe doesn't imply ir3
    cotest.RepeatStep(nodePing6('client', 'ir3.eth0.ir3.home'),
                      wait=1, timeout=TIMEOUT),
    ]

base_6_remote_test = [
    waitRouterPrefix6('200', timeout=TIMEOUT_INITIAL),
    # slight delay acceptable after first-hop router gets address
    cotest.RepeatStep(nodeHasPrefix6('client', '200'),
                      wait=1, timeout=5),
    cotest.RepeatStep(nodePing6('client', 'h-server'),
                      wait=1, timeout=TIMEOUT),
    cotest.RepeatStep(nodePing6('client', 'server.v6.lab.example.com'),
                      wait=1, timeout=TIMEOUT),
    cotest.RepeatStep([updateNodeAddresses6('client', exclude=['fd']),
                       nodePingFromAll6('client', 'h-server')],
                      wait=1, timeout=TIMEOUT),
    #nodeTraceroute6Contains('client', 'h-server', b'cpe.')
    ]

base_6_local_test = [base_6_local_ip_step] + base_6_local_sd_test

base_6_test = base_6_remote_test + base_6_local_test

fw_test = [
    nodeInterfaceFirewallZoneIs('cpe', 'h1', 'wan'),
    nodeInterfaceFirewallZoneIs('cpe', 'h0', 'lan'),
    ]

base_test = [
    startTopology('home7', 'owrt-router'),
    ] + base_6_test + base_4_test + fw_test

class TestCase(cotest.TestCase):
    tearDown = routersNoCrashes()
    tearDownAlways = False

if __name__ == '__main__':
    import logging
    #logging.basicConfig(level=logging.INFO)
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)s %(message)s')
    al = logging.getLogger('asyncio')
    al.setLevel(logging.CRITICAL)
    l = base_test
    l = l + [nodeStop('client'), nodeGo('client'), sleep(1)]
    tc = TestCase(l)
    assert cotest.run(tc)

