#!/bin/bash -ue
#-*-sh-*-
#
# $Id: enable-adhoc-all.sh $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Fri Jun  6 08:41:45 2014 mstenber
# Last modified: Mon Jun 16 12:36:39 2014 mstenber
# Edit time:     2 min
#

# old format, changed 20140615
#uci set network.h0.adhoc=1
uci set network.h0.mode=adhoc
uci set network.h1.mode=adhoc
uci set network.h2.mode=adhoc
uci set network.h3.mode=adhoc
uci commit network

#/etc/init.d/network restart
#restart frequently bugs, should use reload (cyrusff, 20140612)
/etc/init.d/network reload
