#!/bin/bash -ue
#-*-sh-*-
#
# $Id: run_fake.sh $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2013 cisco Systems, Inc.
#
# Created:       Thu Feb  7 13:57:59 2013 mstenber
# Last modified: Wed Jul 17 16:58:20 2013 mstenber
# Edit time:     13 min
#

. /usr/bin/luaenv.sh

mkdir -p $LOGDIR

ENABLE_MST_DEBUG=1 lua $CORE/fakedhcpv6d.lua \
  --join=eth0 \
  --dns=2000::2 \
  --dns=2001:100::1 \
  --search=v6.lab.example.com \
  --pref=3000 \
  --valid=4000 \
  2000:dead:bee0::/56 \
  2000:dead:bee1::/56=42 2>&1 > $LOGDIR/fake.log &

# Implicitly provide for routes also
# (fakedhcpv6d does this automatically, hooray)
#ip -6 route add 2000:dead:bee0::/55 dev eth0 via fe80::ec6e:75ff:fe23:4e28
