#!/bin/bash -ue
#-*-sh-*-
#
# $Id: birdenv.sh $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2013 cisco Systems, Inc.
#
# Created:       Thu Feb  7 14:00:00 2013 mstenber
# Last modified: Wed Apr 10 15:06:39 2013 mstenber
# Edit time:     0 min
#

. /usr/bin/hnetenv.sh

if [ -z $HNET ]
then
    echo "HNET environment variable is not set! Something is wrong"
fi

export CORE=$HNET/component/core
BUILDLUA=$HNET/build/share/lua/5.1
BUILDCLUA=$HNET/build/lib/lua/5.1

export LUA_PATH="$CORE/?.lua;$CORE/thirdparty/?.lua;$BUILDLUA/?.lua;$BUILDLUA/?/init.lua;;"
export LUA_CPATH="$BUILDCLUA/?.so;;"

LOGDIR=/hostlab/logs/`hostname`
#LOGDIR=/tmp

