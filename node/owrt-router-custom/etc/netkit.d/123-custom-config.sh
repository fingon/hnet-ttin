#!/bin/sh
#-*-sh-*-
#
# $Id: 123-custom-config.sh $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Tue Jun 10 17:37:30 2014 mstenber
# Last modified: Tue Jun 10 18:11:51 2014 mstenber
# Edit time:     16 min
#

# Configure any global available
uci batch <<EOF
set hnet.pa.persistent_store=/etc/hnetd.pa_state
set hnet.pa.ip4prefix=172.16.0.0/16
set hnet.sd.router_name=cer
set hnet.sd.domain_name=test.
EOF

uci commit hnet

# Interface-specific things on h0
# covered elsewhere: adhoc, guest (own test caes)
# covering link_id, iface_id, ip{4,6}assign, dnsname
# todo: disable_pa, ula_default_router
uci batch <<EOF
set network.h0.link_id=0/6
set network.h0.ip6assign=62
set network.h0.ip4assign=16
add_list network.h0.iface_id="::42/8 10/8"
add_list network.h0.iface_id="::13/8 2000::/16"
set network.h0.dnsname=h0.test.
EOF

uci commit network

/etc/init.d/network restart




