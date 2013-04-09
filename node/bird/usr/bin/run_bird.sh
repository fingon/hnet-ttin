#!/bin/bash -ue
#-*-sh-*-
#
# $Id: run_bird.sh $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2013 cisco Systems, Inc.
#
# Created:       Thu Feb  7 13:57:59 2013 mstenber
# Last modified: Thu Feb 28 13:31:52 2013 mstenber
# Edit time:     6 min
#

. /usr/bin/birdenv.sh

mkdir -p $LOGDIR

# rewrite the /tmp path in the config file (ugh)
CONF=/etc/bird6.conf
RCONF=/tmp/bird6.conf
cat $CONF > $RCONF
echo "log \"$LOGDIR/bird6.log\" all;" >> $RCONF
if [ ! -f /tmp/elsa.lua ]
then
  ln -s $BIRD/elsa.lua /tmp
fi
ulimit -c unlimited

VALGRIND=
VALARG=
if [ "x$*" = "x-v" ]
then
    (cd /tmp ; ENABLE_MST_DEBUG=1 valgrind bird -d -c $RCONF )
else
    (cd /tmp ; ENABLE_MST_DEBUG=1 bird -c $RCONF )
fi

