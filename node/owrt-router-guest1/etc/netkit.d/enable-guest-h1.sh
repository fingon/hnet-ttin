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
# Last modified: Wed Apr 16 15:51:01 2014 mstenber
# Edit time:     3 min
#

uci set network.h1.mode=guest
uci commit network
/etc/init.d/network restart
