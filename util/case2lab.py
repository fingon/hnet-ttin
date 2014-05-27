#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: case2lab.py $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Created:       Wed Jul  4 11:28:46 2012 mstenber
# Last modified: Tue May 27 11:42:57 2014 mstenber
# Edit time:     514 min
#
"""

This is 'worker' script, which converts case/ => lab/, using the
contents of case/ and template/.

The easy way to undo this is simply to delete the whole lab
subdirectory, it should never be edited by hand.

Basic idea: Look at every subdirectory under case/, that has
case.conf, and produce equivalent lab/ directory, and lab.conf within.

The processing should be .. straightforward.

TODO:

- make utility to produce GraphViz description of the cases and their
  relations, to templates

- make utility to produce GraphViz description of the network topology
  of individual cases (the information should be there)

- generate management interface definitions automatically (for the
  time being, we do it by hand, but that's bit depressing) [ there's a
  race condition somewhere -> doing it just broteforce won't work
  anyway, as the play-with-tap-interface stuff fails ] (see AUTOMGMT
  commented bits)

- v6 reverse zone creation (right now for example ping6 is worth using
  with -n, to prevent delay in reverse lookup.. sigh.)

"""

import pprinter
import re
import os, os.path
import shutil

# keys for case configuration
KEY_MACHINES="machines"
KEY_INHERIT='inherit'
KEY_SKIP='skip'

# keys for node configuration in case
KEY_DEPEND='depend'
KEY_TEMPLATE='template'
KEY_GW='gw'
KEY_IPV6ROUTE='ipv6route'
KEY_NS='ns' # name of the nameserver node
KEY_H='hosts' # hosts configuration - by default, none, hosts=h- prefixed with h-

INTERNAL_LABCONF_KEYS=set([KEY_DEPEND, KEY_GW, KEY_IPV6ROUTE, KEY_NS, KEY_H])

# keys for interface configuration within node configuration
KEY_DHCP='dhcp'
KEY_IPV4='ip'
KEY_IPV6='ipv6'
KEY_IPV6RA='ipv6ra'

SHARED_DIRECTORY='shared'

SHARED_KEYWORD="shared"

CASE_DIRECTORY='case'
CASE_SUFFIX='.conf'

LAB_DIRECTORY='lab'
LAB_FILE='lab.conf'

TEMPLATE_DIRECTORY='template'
TEMPLATE_SUFFIX='.template'

SETUP_SUFFIX='.setup'
STARTUP_SUFFIX='.startup'

INDENT_LEVEL=2

LAB_FILES=['lab.dep', 'shared.startup']

ipv4_re = re.compile('^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$').match

MY_HOSTS_FILENAME='hosts.netkit'
MY_NAMED_ZONE_PREFIX='bind.db.'
MY_NAMED_CONF='named.netkit.conf'

## Start snip (from assorted ms utility collection)

def _allclasses(i):
    def _basesinclself(c):
        r = [c]
        for tc in c.__bases__:
            r.extend(_basesinclself(tc))
        return r
    return _basesinclself(i.__class__)

class ReCollection:
    def __init__(self):
        names = []
        l = []
        for c in _allclasses(self):
            for k, v in c.__dict__.items():
                #print 'considering', k
                if k[-5:] == '_text':
                    base = k[:-5]
                    names.append(base)
                    l.append(v)
                    setattr(self, base + '_match', re.compile(v).match)
                    #print 'adding', base
        self.any_text = '^(%s)$' % '|'.join(l)
        self.any = re.compile(self.any_text).match
        names.sort()
        self.names = names

class ReProcessor:
    res = None # subclass responsibility
    def processLine(self, line):
        res = self.getREs()
        #print line.strip()
        for rename in res.names:
            m = getattr(res, rename + '_match')(line)
            if m is not None:
                #print rename
                f = getattr(self, rename, None)
                if f:
                    f(m)
                return
        raise NotImplementedError, line
    def processLines(self, lines):
        for line in lines:
            self.processLine(line)
    process = processLines # old code compatibility
    def processData(self, data):
        return self.processLines(data.split('\n'))
    def getREs(self):
        assert self.res is not None
        return self.res

class ReCollectionProcessor(ReCollection, ReProcessor):
    def __init__(self):
        ReCollection.__init__(self)
    def getREs(self):
        return self

## End snip (from assorted ms utility collection)

class KVStore:
    def __init__(self):
        self.hkv = {}
    def addKV(self, k, v):
        self._addHKV(None, k, v)
    def _addHKV(self, h, k, v):
        th = self.hkv.setdefault(h, {})
        th[k] = v

    parse_kv_text = '^\s*([0-9a-zA-Z][^#\[=]*)\s*=\s*(.*)$'
    def parse_kv(self, m):
        l = m.groups()
        #print 'kv', l
        assert len(l) == 2
        self.addKV(*l)

    z_text='^.*$'
    def z(self, m):
        pass



class HKVStore(KVStore):
    def addHKV(self, *args):
        self._addHKV(*args)

    parse_hkv_text = '^\s*([a-zA-Z][^#\[]*)\s*\[([^\]]+)\]\s*=\s*(.*)$'
    def parse_hkv(self, m):
        l = m.groups()
        #print 'hkv', l
        assert len(l) == 3
        self.addHKV(*l)


class Template(ReCollectionProcessor, KVStore):
    def __init__(self, cdb, name, path):
        self.cdb = cdb
        self.name = name
        self.path = os.path.abspath(path)
        KVStore.__init__(self)
        ReCollectionProcessor.__init__(self)
    def getTemplateBasePath(self):
        return self.path
    def getParents(self):
        d = self.hkv.get(None, {})
        p = d.get(KEY_INHERIT)
        if p:
            return map(lambda x:self.cdb.getTemplate(x.strip()),
                       p.split(','))
    def getInheritedKV(self):
        pl = self.getParents()
        d = self.hkv.get(None, {})
        if not pl:
            return d
        d2 = {}
        for p in pl:
            d2.update(p.getInheritedKV().copy())
        d = d.copy()
        d.pop(KEY_INHERIT)
        d2.update(d)
        return d2
    def getTemplates(self):
        pl = self.getParents()
        if pl:
            for p in pl:
                for pt in p.getTemplates():
                    yield pt
        yield self
    def iterateInstances(self, conf, k, fun):
        for t in self.getTemplates():
            fun(conf, k, None, t)

class PPStore:
    """ This class represents a bunch of (similar) files, that are
    written to using PrettyPrinter interface. Basic assumption is to
    initialize it somewhere, and after that get() every now and then
    as needed
    """
    def __init__(self, format, defaults=None):
        self.defaults = defaults
        self.format = format
        self.h = {}
    def getPP(self, k):
        if not self.h.has_key(k):
            path = self.format % k
            dirname = os.path.dirname(path)
            os.system('mkdir -p %s' % dirname)
            f = open(path, 'w')
            pp = pprinter.DelayedPrettyPrinter(f, INDENT_LEVEL)
            if self.defaults:
                for line in open(self.defaults):
                    pp(line.rstrip())
            self.h[k] = pp
        return self.h[k]

class NameWriter:
    def __init__(self, bp, h, ns, admin='nobody'):
        self.n2a = {}
        self.bp = bp
        self.h = h
        self.ns = ns
        self.admin = admin
    def add(self, address, f, name):
        ak = address
        #ak = (address, f)
        nk = (name, f)
        if not self.n2a.has_key(nk):
            self.n2a[nk] = ak
    def getA2N(self):
        """ Create (address, family) => [list of names] hash """
        a2n = {}
        for (n, f), a in self.n2a.items():
            #ak = (a, f)
            ak = (a, f)
            l = a2n.setdefault(ak, [])
            if self.h:
                n = self.h + n
            l.append(n)
        return a2n
    def dump(self):
        if self.h is not None:
            self.dumpHosts()
        if self.ns:
            self.dumpBind()
    def dumpBindOne(self, zones, domain, zone, v1, f1, f2, v2):
        #print locals()
        if not zone:
            zone = domain
        if not zones.has_key(zone):
            fname = MY_NAMED_ZONE_PREFIX + zone
            zones[zone] = (fname, pprinter.PrettyPrinter(open(os.path.join(self.bp, fname), "w")), {})
            pp = zones[zone][1]
            ns = self.ns
            admin = self.admin
            if zone == domain:
                pp('''
;
; auto-generated BIND data for %(zone)s
;
$TTL 3h
@\tIN\tSOA\t%(ns)s.%(domain)s. %(admin)s.%(domain)s. (1 3h 1h 1w 1h)
@\tIN\tNS\t%(ns)s.%(domain)s.

ns\tIN\tCNAME\t%(ns)s


''' % locals())
            else:
                pp('''
;
; auto-generated BIND reverse data for %(zone)s / %(domain)s
;
$TTL 3h
@\tIN\tSOA\tns.%(domain)s. %(admin)s.%(domain)s. (1 3h 1h 1w 1h)
@\tIN\tNS\tns.%(domain)s.

''' % locals())
        z = zones[zone]
        pp = z[1]
        dh = z[2]
        if dh.has_key(v1):
            return
        dh[v1] = (f1, f2, v2)
        pp('%(v1)s\t%(f1)s\t%(f2)s\t%(v2)s' % locals())
    def dumpBindV6(self, addr, names, zones):
        for name in names:
            domain = 'v6.lab.example.com'
            self.dumpBindOne(zones, domain, None, name, 'IN', 'AAAA', addr)
    def dumpBindV4(self, addr, names, zones):
        # Generate zones per /24
        l = addr.split('.')
        assert len(l) == 4
        tl = l[:3]
        tl.reverse()
        rzone = '%s.in-addr.arpa' % ('.'.join(tl))
        #rname = '%s.%s.' % (l[3], rzone)
        rname = '%s' % l[3]
        for name in names:
            domain = 'v4.lab.example.com'
            self.dumpBindOne(zones, domain, None, name, 'IN', 'A', addr)
            fullnamedot = '%s.%s.' % (name, domain)
            self.dumpBindOne(zones, domain, rzone, rname, 'IN', 'PTR', fullnamedot)
    def dumpBind(self):
        """ Create BIND zones to /etc:
- bind.db.lab.example.com
- bind.db.v4.lab.example.com
- bind.db.v6.lab.example.com
- .. and the assorted reverse zones

- and named.netkit.conf (which uses the bind.db.* to do things)
"""
        zones = {}
        a2n = self.getA2N()
        it = a2n.items()
        it.sort()
        #print it
        for (a, af), l in it:
            # dump shortest name -> longest => first ones override later ones
            l.sort(lambda x,y:cmp(len(x), len(y)))
            if af == KEY_IPV4:
                self.dumpBindV4(a, l, zones)
            else:
                self.dumpBindV6(a, l, zones)
        nncpp = pprinter.PrettyPrinter(open(os.path.join(self.bp, MY_NAMED_CONF), 'w'))
        for k, (v, pp, dh) in zones.items():
            nncpp('zone "%(k)s" { type master ; file "/etc/%(v)s"; };' % locals())

    def dumpHosts(self):
        hpp = pprinter.PrettyPrinter(open(os.path.join(self.bp, MY_HOSTS_FILENAME), 'w'))
        hpp('# NETKIT magic! (Used to prevent multiple insertion')
        # Base logic: For each _address_, dump applicable _names_,
        # with the longest first (so it's most descriptive)
        a2n = self.getA2N()
        it = a2n.items()
        it.sort()
        for (a, af), l in it:
            l.sort(lambda x,y:cmp(len(x), len(y)))
            l.reverse()
            ls = ' '.join(l)
            av = a
            #av = a[0]
            hpp('%(av)s\t%(ls)s' % locals())

class Configuration(ReCollectionProcessor, HKVStore):
    """ This class represents a single configuration with bunch of
    host[key]=value, or key=value

    It is used to represent the case.conf files useful content
    """
    lab = None
    def __init__(self, cdb, name, path):
        self.cdb = cdb
        self.name = name
        self.path = os.path.abspath(path)
        HKVStore.__init__(self)
        ReCollectionProcessor.__init__(self)
    def _addHKV(self, h, k, v):
        if k == KEY_TEMPLATE:
            v = self.cdb.replace_template.get(v, v)
        HKVStore._addHKV(self, h, k, v)
    def __repr__(self):
        return '<Configuration "%s">' % (self.name)
    def getParent(self):
        inh = self.getKV().get(KEY_INHERIT, None)
        if inh:
            return self.cdb.getCase(inh)
    def getTemplatedHKV(self, i):
        # Convert the stuff to obey templates if any
        r = {}
        for k, d in i.items():
            d = d.copy()
            t = d.pop(KEY_TEMPLATE, None)
            if t:
                d2 = self.cdb.getTemplate(t).getInheritedKV().copy()
                d2.update(d)
                d = d2
            r[k] = d
        return r
    def getHKV(self, inherit=True, expand=True, depth=0, nodes=None):
        if nodes is None:
            nodes = self.getActiveNodes()

        # Merge two hash of hashes, with values from hh2 overriding
        # values in hh1
        def _merge(hh1, hh2):
            r = {}
            for k, d in hh1.items():
                r[k] = d.copy()
            for k, d2 in hh2.items():
                d = r.setdefault(k, {})
                d.update(d2)
            return r
        def _rewrite_shared(h, copied):
            if not h.has_key(SHARED_KEYWORD) or not nodes:
                return h
            if not copied:
                h = h.copy()
            sh = h.pop(SHARED_KEYWORD)
            assert sh
            for n in nodes:
                if h.has_key(n):
                    h2 = h[n].copy()
                else:
                    h2 = {}
                h[n] = h2
                for k, v in sh.items():
                    if not h2.has_key(k):
                        h2[k] = v
            return h
        if inherit:
            ic = self.getParent()
        else:
            ic = False
        if ic:
            # Need to expand templates only once - in the end
            hh1 = ic.getHKV(inherit=True, expand=False, depth=depth+1, nodes=nodes).copy()
            hh2 = _rewrite_shared(self.hkv.copy(), True)
            # Get rid of inherit
            d = hh2[None].copy()
            d.pop(KEY_INHERIT)
            hh2[None] = d
            t = _merge(hh1, hh2)
        else:
            t = _rewrite_shared(self.hkv, False)
        if expand:
            t = self.getTemplatedHKV(t)
        #print depth, 'GIH', t
        return t

    def KVToPP(self, k, v, pp, upper):
        if upper and upper.get(k, None):
            return
        if k in KEY_INHERIT:
            return
        pp('%s=%s' % (k, v))
    def HKVToPP(self, h, k, v, pp, depth, upper):
        if upper and upper.get((h,k), None):
            return
        assert k != KEY_TEMPLATE # should be processed elsewhere
        # KEY_GW is handled in startup scripts
        if k in INTERNAL_LABCONF_KEYS:
            return
        # Consider if it looks like ethernet specification
        if len(k) == 1 and k.isdigit():
            # just dump network definitions at root level
            if depth:
                return
            # Yay, it is.
            l = v.split(',')
            if len(l)>1 and l[0] != 'tap':
                v = l[0]
                # just leave the name of the network - the size should be non
                assert len(v) > 0
        pp('%(h)s[%(k)s]=%(v)s' % locals())

    def toPP(self, pp, depth=0, upper=None):
        hs = self.hkv.copy()
        # Dump to string. Note: inherit is processed here
        d = hs.pop(None, {})
        it = d.items()
        it.sort()
        hs = self.getTemplatedHKV(hs)
        it2 = hs.items()
        it2.sort()
        if upper:
            mine = upper.copy()
        else:
            mine = {}
        for k, v in it:
            mine[k] = True
        for h, d in it2:
            it3 = d.items()
            for k, v in it3:
                mine[h,k] = True
        ic = self.getParent()
        if ic:
            pp('# start - from inherited %s' % ic.name)
            pp.indent()
            ic.toPP(pp, depth+1, mine)
            pp.dedent()
            pp('# end - from inherited %s' % ic.name)

        for k, v in it:
            self.KVToPP(k, v, pp, upper)
        for h, d in it2:
            it3 = d.items()
            it3.sort()
            for k, v in it3:
                self.HKVToPP(h, k, v, pp, depth+1, upper)
    def toLab(self, cdir):
        self.lab = os.path.abspath(cdir)

        kv = self.getInheritedKV()
        if kv.get(KEY_SKIP):
            #print ' skipping'
            return


        ihkv = self.getHKV()

        # First off, make the directory
        os.system('mkdir -p "%s"' % cdir)

        # Then, initialize lab.conf
        fname = os.path.join(cdir, LAB_FILE)
        f = open(fname, 'w')
        pp = pprinter.PrettyPrinter(f, INDENT_LEVEL)

        nodes = self.getActiveNodes()
        nodes.sort()
        pp('# Active nodes %s' % nodes)
        for k, d in self.getInheritedInstances(expand=False):
            if k not in nodes:
                continue
            t = d.get(KEY_TEMPLATE, None)
            if t:
                pp('# %s[%s] = %s' % (k,KEY_TEMPLATE, t))

        addresses = self.toPP(pp)

        addresses = {}
        ras = {}
        rid = 2
        pp('# start (inherited) interface definitions')
        #print ihkv
        for h in nodes:
            d = ihkv[h]
            for k, v in d.items():
                if len(k) == 1 and k.isdigit():
                    self.HKVToPP(h, k, v, pp, 0, None)
            # AUTOMGMT - disabled for now
            if 0:
                myip = '192.168.7.%d' % rid
                rid += 1
                pp('%s[9]=tap,192.168.7.1,%s' % (h, myip))
                addresses[h, '9', KEY_IPV4] = myip
        pp('# end (inherited) interface definitions')

        # Then, copy files, in inheritance hierarchy order
        # (so that the overwrite will work correctly)
        self.iterateCaseInstances(self.iteratedCopyDirectory)

        # Run the setup scripts, in inheritance hierarchy order
        self.iterateCaseInstances(self.iteratedRunSetupScripts)

        # Then, copy case-specific stuff
        for conf in self.getCases():
            self.copyCaseData(conf, self)

        # Finally create startup files
        startups = PPStore(os.path.join(self.lab, '%s' + STARTUP_SUFFIX))

        def _dump(fname, k):
            if not os.path.isfile(fname):
                return
            pp = startups.getPP(k)
            pp('# start from %s' % fname)
            pp.indent()
            for line in open(fname):
                pp(line.strip())
            pp.dedent()
            pp('# end from %s' % fname)
            pp('')

        net_nondhcp = {}
        net_dhcp = {}

        # Start with interface configuration stuff (so .startup's can
        # override it)
        for h in nodes:
            pp = startups.getPP(h)
            d = ihkv[h]
            for k, v in d.items():
                if len(k) == 1 and k.isdigit():
                    l = v.split(',')
                    if len(l) > 1 and l[0] != 'tap':
                        # interface specification
                        iface = 'eth%s' % k
                        pp('# autoconfigure %s' % iface)
                        pp('ifconfig %s up' % iface)
                        dhcp = False
                        for e in l[1:]:
                            if e == KEY_DHCP:

                                pp('# fire up dhclient to configure interface')
                                pp('dhclient %s' % iface)
                                dhcp = True
                                continue
                            if e == KEY_IPV6RA:
                                e = e + ':'
                            if ':' not in e:
                                # See if it looks like ipv4 address
                                if ipv4_re(e) is not None:
                                    e=KEY_IPV4+':'+e
                            assert ':' in e, 'invalid iface autospec: %s' % e
                            ik, iv = e.split(':', 1)
                            if ik == KEY_IPV4:
                                ivl = iv.split('/')
                                addresses[h, k, KEY_IPV4] = [ivl[0]]
                                assert len(ivl) <= 2
                                pp('ifconfig %s %s' % (iface, ' '.join(ivl)))
                                continue
                            elif ik == KEY_IPV6:
                                nml = iv.split('/')
                                #pp('modprobe ipv6 # just in case')
                                pp('ip -6 addr add %(iv)s dev %(iface)s' % locals())
                                key = (h, k, KEY_IPV6)
                                tl = addresses.setdefault(key, [])
                                tl.append(nml[0])
                                continue
                            elif ik == KEY_IPV6RA:
                                key = (h, k)
                                rl = ras.setdefault(key, [])
                                if iv:
                                    rl.append(iv)
                                continue
                            raise NotImplementedError, 'unknown iface spec: %s' % e
                        if dhcp:
                            net_dhcp.setdefault(l[0], []).append(h)
                        else:
                            net_nondhcp.setdefault(l[0], []).append(h)
                    elif l[0] == 'tap':
                        assert len(l) == 3
                        addresses[h, k, KEY_IPV4] = [l[2]]
                        pp('# remove default gw to admin host by default (if netkit somehow makes it) - it may hinder dhclient')
                        pp('route delete default gw %s 2>/dev/null' % l[1])
                elif k == KEY_IPV6ROUTE:
                    for s in v.split(','):
                        if s:
                            l = s.split(' ')
                            assert len(l) == 2
                            s = '%s via %s' % tuple(l)
                            pp('ip -6 route add %s' % s)

        # Then add default gw, if any (it has to be done AFTER
        # interfaces are added)
        for h in nodes:
            d = ihkv[h]
            for k, v in d.items():
                if k == KEY_GW:
                    # gateway specification
                    pp = startups.getPP(h)
                    pp('# add default gw')
                    pp('route add default gw %s' % v)

        # Add /etc/hosts configuration stuff to EVERY host
        for h in nodes:
            d = ihkv[h]

            bp = os.path.join(self.getLabPath(), h, 'etc')
            os.system('mkdir -p "%s"' % bp)
            pp = startups.getPP(h)

            pp('# Enable IPv4 forwarding by default')
            pp('echo 1 > /proc/sys/net/ipv4/ip_forward')

            if d.has_key(KEY_H):
                pp('# insert the /etc/%s, if it is helpful' % MY_HOSTS_FILENAME)
                pp('if ! grep -q NETKIT /etc/hosts')
                pp('then')
                pp.indent()
                pp('cat /etc/%s >> /etc/hosts' % MY_HOSTS_FILENAME)
                pp.dedent()
                pp('fi')

            nw = NameWriter(bp, d.get(KEY_H, None), d.get(KEY_NS, None))
            it = addresses.items()
            for (h, i, f), l in it:
                for v in l:
                    if f == KEY_IPV4:
                        afp = '4'
                    else:
                        afp = '6'
                    n1 = '%(h)s-eth%(i)s-ipv%(afp)s' % locals()
                    n2 = '%(h)s-eth%(i)s' % locals()
                    n3 = h
                    for n in [n1, n2, n3]:
                        nw.add(v, f, n)
            nw.dump()

        # Set up radvd if necessary
        for ho in nodes:
            pp = None
            for (h, k), l in ras.items():
                if ho != h:
                    continue
                if pp is None:
                    etc = os.path.join(self.getLabPath(), h, 'etc')
                    os.system('mkdir -p "%s"' % etc)
                    f = open(os.path.join(etc, "radvd.conf"), 'w')
                    pp = pprinter.PrettyPrinter(f)
                al = addresses.get((h, k, KEY_IPV6), [])
                pp('interface eth%s {' % k)
                pp.indent()
                pp('AdvSendAdvert on;')
                pp('AdvManagedFlag off;')
                pp('AdvOtherConfigFlag off;')
                pp('AdvDefaultLifetime 600;')
                if not al:
                    al = ['::/64']
                for p in al:
                    if '/' not in p:
                        p += '/64'
                    pp('prefix %s {' % p)
                    pp.indent()
                    pp('AdvOnLink on;')
                    pp('AdvAutonomous on;')
                    pp.dedent()
                    pp('};')
                pp.dedent()
                pp('};')
            if pp is not None:
                pp = startups.getPP(ho)
                pp('# enable ipv6 forwarding')
                pp('echo 1 > /proc/sys/net/ipv6/conf/all/forwarding')
                pp('')
                pp('# start radvd')
                pp('chmod 0600 /etc/radvd.conf')
                pp('radvd')
                pp('')

        # Then actual .startup's, in template-inheritance order
        # (we don't expand templates intentionally, but we want the most
        # up-to-date template definition only)
        for k, d in self.getInheritedInstances(expand=False):
            if k not in nodes:
                continue
            t = d.get(KEY_TEMPLATE, None)
            if t:
                t = self.cdb.getTemplate(t)
                for t in t.getTemplates():
                    fname = t.getTemplateBasePath() + STARTUP_SUFFIX
                    _dump(fname, k)
        for case in self.getCases():
            for k, d in case.getInstances():
                if k not in nodes:
                    continue
                # Templates taken care of - what about case-specific
                # configuration?
                fname = os.path.join(case.getCasePath(), k + STARTUP_SUFFIX)
                _dump(fname, k)

        # Write lab.dep if it does not exist
        filepath = os.path.join(self.getLabPath(), 'lab.dep')
        if not os.path.isfile(filepath):
            pp = pprinter.PrettyPrinter(open(filepath, 'w'))
            # Look at explicit depend statements
            rdeps = {}
            for k, d in self.getInheritedInstances():
                if k not in nodes:
                    continue
                dhcp_nets = map(lambda x:x[0], filter(lambda x:k in x[1], net_dhcp.items()))
                deps = []
                for net in dhcp_nets:
                    for n in net_nondhcp.get(net, []):
                        deps.append(n)

                dep = d.get(KEY_DEPEND, None)
                if dep:
                    deps.append(dep)
                if deps:
                    s = ' '.join(deps)
                    rdeps[k,s]=1
            for k, s in rdeps.keys():
                pp('%(k)s: %(s)s' % locals())

    def getActiveNodes(self):
        kv = self.getInheritedKV()
        mk = kv[KEY_MACHINES] # mandatory field
        mk = mk.strip()
        # Strip string quoting if any
        if mk[0] == '"':
            assert mk[-1] == '"'
            mk = mk[1:-1]
        return mk.split(" ")
    def getCasePath(self):
        assert self.path
        return self.path

    def getLabPath(self):
        assert self.lab, self
        return self.lab

    def getCases(self):
        p = self.getParent()
        if not p:
            return [self]
        return p.getCases() + [self]
    def getInstances(self):
        for k, d in self.getHKV(expand=False, inherit=False).items():
            if not k:
                continue
            yield k, d
    def getKV(self):
        return self.hkv.get(None, {})
    def getInheritedKV(self):
        return self.getHKV(expand=False,nodes=False).get(None, {})
    def getInheritedInstances(self, **kwargs):
        for k, d in self.getHKV(**kwargs).items():
            if not k:
                continue
            yield k, d
    def iterateCaseInstances(self, fun, *args):
        nodes = self.getActiveNodes()

        # Figure which case # we should start caring about after; the
        # previous ones are completely overridden by template=
        # (multiple inheritance of cases+templates is something I want
        # to avoid)
        n = 1
        templated = {}
        for conf in self.getCases():
            for k, d in conf.getInstances():
                if d.has_key(KEY_TEMPLATE):
                    templated[k] = n
            conf.n = n
            n = n + 1

        for conf in self.getCases():
            for k, d in conf.getInstances():
                if k not in nodes:
                    continue
                if templated.get(k, 0) > conf.n:
                    continue
                t = d.get(KEY_TEMPLATE, None)
                if t:
                    t = self.cdb.getTemplate(t)
                    t.iterateInstances(self, k, fun, *args)
                fun(self, k, conf, None, *args)
    def iteratedCopyDirectory(self, dc, k, c, t):
        def _process(sd, dd):
            #dd = os.path.join(dc.getLabPath(), k)
            #print 'considering', sd
            if os.path.isdir(sd):
                self.rsync(sd+'/', dd)
        assert k
        dd = os.path.join(dc.getLabPath(), k)
        if c:
            sd = os.path.join(c.getCasePath(), SHARED_DIRECTORY)
            _process(sd, dd)

            sd = os.path.join(c.getCasePath(), k)
            _process(sd, dd)
            return
        assert t
        sd = t.getTemplateBasePath()
        _process(sd, dd)
    def iteratedRunSetupScripts(self, dc, k, c, t):
        def _process(ss, sd, dd, k):
            #print 'checking', ss
            if not os.path.isfile(ss):
                return
            cmd = 'sh "%(ss)s" "%(sd)s" "%(dd)s" "%(k)s"' % locals()
            print 'running', cmd
            os.system(cmd)
            #print 'should run', cmd
        assert k
        dd = dc.getLabPath()
        if c:
            sd = os.path.join(c.getCasePath())
            ss = os.path.join(sd, k + SETUP_SUFFIX)
            _process(ss, sd, dd, k)
        else:
            p = t.getTemplateBasePath()
            sd = os.path.dirname(p)
            ss = p + SETUP_SUFFIX
            _process(ss, sd, dd, k)

    def copyCaseData(self, scase, dcase):
        for filename in LAB_FILES:
            spath = os.path.join(scase.getCasePath(), filename)
            if not os.path.isfile(spath):
                #print 'no', spath
                continue
            dpath = os.path.join(dcase.getLabPath(), filename)
            self.copy(spath, dpath)
    def copy(self, spath, dpath):
        shutil.copyfile(spath, dpath)
        print 'copying', spath, dpath
    def rsync(self, spath, dpath):
        print 'rsync', spath, dpath
        os.system("rsync -a '%(spath)s' '%(dpath)s'" % locals())

class ConfigurationDatabase:
    def __init__(self, replace_template, lab_filter):
        self.c = {}
        self.t = {}
        self.replace_template = replace_template
        self.lab_filter = lab_filter
        # Read everything under case/
        for filename in os.listdir(CASE_DIRECTORY):
            cpath = os.path.join(CASE_DIRECTORY, filename)
            if not os.path.isfile(cpath):
                continue
            if not cpath.endswith(CASE_SUFFIX):
                continue
            npath = cpath[:-len(CASE_SUFFIX)]
            cname = filename[:-len(CASE_SUFFIX)]
            #print cpath, filename, cname
            conf = Configuration(self, cname, npath)
            conf.processLines(open(cpath))
            assert conf.hkv
            self.c[cname] = conf
        # Read everything under template/ that ends in TEMPLATE_SUFFIX
        for filename in os.listdir(TEMPLATE_DIRECTORY):
            npath = os.path.join(TEMPLATE_DIRECTORY, filename)
            if not os.path.isfile(npath):
                continue
            if not filename.endswith(TEMPLATE_SUFFIX):
                continue
            tname = filename[:-(len(TEMPLATE_SUFFIX))]
            #print tname
            template = Template(self, tname, os.path.join(TEMPLATE_DIRECTORY, tname))
            template.processLines(open(npath))
            #assert template.hkv, npath # empty templates are ok,
            # as they may just contain utility files..
            self.t[tname] = template

    def writeLabs(self):
        it = self.c.items()
        it.sort()
        for cname, c in it:
            if not self.lab_filter or cname in self.lab_filter:
                cdir = os.path.join(LAB_DIRECTORY, cname)
                print '.. setting up', cdir
                c.toLab(cdir)

    def getCase(self, name):
        return self.c[name]
    def getTemplate(self, name):
        # This is not good idea, may lead to inheritance loops
        # if replacing with child template
        #name = self.replace_template.get(name, name)
        return self.t[name]

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('lab',
                    nargs='*',
                    help="Build out only specific labs (by default, all are built).")
    ap.add_argument('--replace-template',
                    action='append',
                    help='Replace template X with template Y (given as X=Y)'
                    )
    replace_template = {}
    args = ap.parse_args()
    for s in args.replace_template or []:
        l = s.split('=')
        assert len(l) == 2, 'weird content:%s' % l
        k, v = l
        replace_template[k] = v
    cdb = ConfigurationDatabase(replace_template, args.lab)
    cdb.writeLabs()



