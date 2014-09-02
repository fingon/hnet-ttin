#!/bin/bash -ue
#-*-sh-*-
#
# $Id: change-etc-dibbler-pd-length-to-64.sh $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Thu Apr  3 14:22:04 2014 mstenber
# Last modified: Thu Apr  3 14:22:39 2014 mstenber
# Edit time:     1 min
#

CONF=/etc/dibbler/server.conf

perl -i.bak -pe 's/pd-length 56/pd-length 62/' $CONF 

