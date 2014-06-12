#!/bin/bash -ue
#-*-sh-*-
#
# $Id: enable-guest-h1.sh $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Wed Apr 16 13:50:23 2014 mstenber
# Last modified: Thu Jun 12 11:41:46 2014 mstenber
# Edit time:     3 min
#

uci set network.h1.guest=1
uci commit network
#/etc/init.d/network restart
#restart frequently bugs, should use reload (cyrusff, 20140612)
/etc/init.d/network reload
