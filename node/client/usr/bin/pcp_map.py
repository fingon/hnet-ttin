#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: pcp_map.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Mon Jun  2 17:05:05 2014 mstenber
# Last modified: Wed Apr 22 10:25:33 2015 mstenber
# Edit time:     72 min
#
"""

This is minimalist PCP map utility which leverages scapi and scapi_pcp
to do the dirty work.

It performs PCP map operation either towards default route on IPv4, or
IPv6, and returns the mapped _address_ and port.

"""

from scapy.all import sr1, conf, IP, IPv6, UDP, log_runtime
from scapy_pcp import PCP
import re
import argparse
import random

# Workaround to get log messages from socket failures in Scapy 2.2
import scapy.supersocket

#scapy.supersocket.log_runtime = log_runtime
class Foo:
    def error(*args, **kwargs):
        raise
scapy.supersocket.log_runtime = Foo()

parser = argparse.ArgumentParser(description='PCP map tool')
parser.add_argument('-T', '--tcp', action='store_true')
parser.add_argument('-U', '--udp', action='store_true')
parser.add_argument('-4', '--ipv4', action='store_true')
parser.add_argument('-6', '--ipv6', action='store_true')
parser.add_argument('-a', '--announce', action='store_true')
parser.add_argument('-p', '--port', type=int, help='port number')
parser.add_argument('-i', '--ip', type=str, help='internal ip')
parser.add_argument('-t', '--timeout', type=int, default=1, help='timeout')

ipv4_re = re.compile('^([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)$')

def is_ipv4(host):
    return host and ipv4_re.match(host) is not None

def to_v6ish(host):
    if not host:
        return host
    if is_ipv4(host):
        host = '::ffff:' + host
    return host

def handle_one(p, iface, timeout):
    print p.show()
    reply = sr1(p, iface=iface, retry=0, timeout=timeout)

    if reply:
        print reply.show()
        if reply.opcode != 128 and reply.ext_port > 0:
            print 'got', reply.ext_ip, reply.ext_port


if __name__ == '__main__':
    import sys
    args = parser.parse_args()
    host = to_v6ish(args.ip)
    port = args.port
    protocol = 0
    opcode = 1
    if args.announce:
        opcode = 0
    if args.tcp:
        protocol = 6
    elif args.udp:
        protocol = 17
    p = PCP(opcode=opcode)
    if opcode:
        assert protocol, 'choose -t or -u'
        assert port, 'choose port'
        p.protocol = protocol
        p.int_port = port
    if is_ipv4(args.ip) or args.ipv4:
        #print conf.route.routes
        for r in conf.route.routes:
            if r[0] or r[1]:
                continue
            host = host or str(r[-1])
            host = to_v6ish(host)
            p.src_ip = host
            p = IP(dst=r[2]) / UDP(sport=5350) / p
            handle_one(p, None, timeout=args.timeout)
            break
    else:
        for r in conf.route6.routes:
            if r[0] != '::':
                continue
            l = [host]
            if not host:
                l = r[-1]
            for h in l:
                h = str(h)
                # Ignore ULA
                if h.startswith('fd'):
                    continue
                #dst = r[2] + ' %' + r[3]
                dst = r[2]
                iface = r[3]
                p.src_ip = h
                # If sending more than one, we have to use different nonces
                p.nonce1 = random.randint(0,0xffffffff)
                p.nonce2 = random.randint(0,0xffffffff)
                p.nonce3 = random.randint(0,0xffffffff)

                rp = IPv6(src=h, dst=dst) / UDP(sport=1234) / p
                handle_one(rp, iface, timeout=args.timeout)
            break
