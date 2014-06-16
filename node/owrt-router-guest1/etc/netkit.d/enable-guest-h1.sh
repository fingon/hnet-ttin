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
# Last modified: Mon Jun 16 12:36:41 2014 mstenber
# Edit time:     3 min
#

# old format, changed 20140615
#uci set network.h1.guest=1
uci set network.h1.mode=guest
uci commit network
#/etc/init.d/network restart
#restart frequently bugs, should use reload (cyrusff, 20140612)
/etc/init.d/network reload
