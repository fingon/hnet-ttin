#!/bin/bash -ue
#-*-sh-*-
#
# $Id: fix-dnsmasq.sh $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2015 cisco Systems, Inc.
#
# Created:       Mon May 25 10:44:41 2015 mstenber
# Last modified: Mon May 25 10:46:18 2015 mstenber
# Edit time:     1 min
#

# boguspriv = 1 seems to be default nowadays in OpenWrt. Running on
# the hybrid cases, for example, that breaks our double NAT ISP :-) Oh
# well. Fix that here.

uci set dhcp.@dnsmasq[0].boguspriv='0'
uci commit dhcp
/etc/init.d/dnsmasq restart
