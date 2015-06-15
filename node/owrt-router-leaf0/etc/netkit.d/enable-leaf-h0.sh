#!/bin/bash -ue
#-*-sh-*-
#
# $Id: enable-leaf-h0.sh $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2015 cisco Systems, Inc.
#
# Created:       Mon Jun 15 11:57:07 2015 mstenber
# Last modified: Mon Jun 15 11:57:37 2015 mstenber
# Edit time:     0 min
#

uci set network.h0.mode=leaf
uci commit network

#/etc/init.d/network restart
#restart frequently bugs, should use reload (cyrusff, 20140612)
/etc/init.d/network reload
