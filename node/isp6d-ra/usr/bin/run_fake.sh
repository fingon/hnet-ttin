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
# Last modified: Tue Mar 12 16:52:35 2013 mstenber
# Edit time:     11 min
#

. /usr/bin/birdenv.sh

mkdir -p $LOGDIR

ENABLE_MST_DEBUG=1 lua $BIRD/lua/fakedhcpv6d.lua \
  --join=eth0 \
  --dns=2000::2 \
  --search=v6.lab.example.com \
  --pref=3000 \
  --valid=4000 \
  2000:dead:bee0::/56 \
  2000:dead:bee1::/56=42 2>&1 > $LOGDIR/fake.log &

# Implicitly provide for routes also
# (fakedhcpv6d does this automatically, hooray)
#ip -6 route add 2000:dead:bee0::/55 dev eth0 via fe80::ec6e:75ff:fe23:4e28
