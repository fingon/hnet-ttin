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
# Last modified: Thu Feb 19 12:29:43 2015 mstenber
# Edit time:     53 min
#

# Configure any global available
uci batch <<EOF
set hnet.pa.persistent_store=/etc/hnetd.pa_state
set hnet.pa.ip4prefix=172.16.0.0/12
set hnet.sd.router_name=cer
set hnet.sd.domain_name=test.
EOF

uci commit hnet

# Interface-specific things on h0
# covered elsewhere: adhoc, guest (own test caes)
# covering link_id, iface_id, ip{4,6}assign, dnsname
# todo: disable_pa, ula_default_router
uci batch <<EOF
set network.h0.link_id=7/4
set network.h0.ip4assign=16
set network.h0.ip6assign=60
set network.h0.iface_id="::0D/4@172.0.0.0/8 ::42/8@2000::/16"
set network.h0.prefix=2000:feed:dead::/64
set network.h0.dnsname=h0.test.
EOF

#0D = 13

uci commit network

#/etc/init.d/network restart
#restart frequently bugs, should use reload (cyrusff, 20140612)
#/etc/init.d/network reload

# This is necessary if not running the -debug variant. However,
# as we're testing the argument parsing here, the -debug build is not really 
# applicable in general.
#/etc/init.d/hnetd restart

# (The official way(tm))
reload_config



