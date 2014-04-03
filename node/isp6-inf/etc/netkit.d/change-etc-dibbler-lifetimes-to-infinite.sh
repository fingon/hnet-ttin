#!/bin/bash -ue
#-*-sh-*-
#
# $Id: change-etc-dibbler-lifetimes-to-infinite.sh $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Thu Apr  3 14:10:49 2014 mstenber
# Last modified: Thu Apr  3 14:11:47 2014 mstenber
# Edit time:     0 min
#

CONF=/etc/dibbler/server.conf

perl -pe 's/300/4294967295/' < $CONF |
perl -pe 's/600/4294967295/' > $CONF.new

mv $CONF.new $CONF

