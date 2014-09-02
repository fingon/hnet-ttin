#!/bin/bash -ue
#-*-sh-*-
#
# $Id: enable-hybrid-h0.sh $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Mon Jun 16 13:00:19 2014 mstenber
# Last modified: Tue Sep  2 11:16:28 2014 mstenber
# Edit time:     1 min
#

uci set network.h0.mode=hybrid
uci set network.h0.reqprefix=58
uci commit network

#/etc/init.d/network restart
#restart frequently bugs, should use reload (cyrusff, 20140612)
/etc/init.d/network reload
