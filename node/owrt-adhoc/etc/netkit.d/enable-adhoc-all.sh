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
# Last modified: Fri Jun  6 08:42:06 2014 mstenber
# Edit time:     1 min
#

uci set network.h0.mode=adhoc
uci set network.h1.mode=adhoc
uci set network.h2.mode=adhoc
uci set network.h3.mode=adhoc
uci commit network
/etc/init.d/network restart
