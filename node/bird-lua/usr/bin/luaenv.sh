#!/bin/bash -ue
#-*-sh-*-
#
# $Id: luaenv.sh $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2013 cisco Systems, Inc.
#
# Created:       Thu Feb  7 14:00:00 2013 mstenber
# Last modified: Wed May 22 14:24:59 2013 mstenber
# Edit time:     6 min
#

. /usr/bin/hnetenv.sh

if [ -z $HNET ]
then
    echo "HNET environment variable is not set! Something is wrong"
fi

BUILDLUA=$BUILD/share/lua/5.1
BUILDCLUA=$BUILD/lib/lua/5.1

export LUA_PATH="$CORE/?.lua;$CORE/thirdparty/?.lua;$BUILDLUA/?.lua;$BUILDLUA/?/init.lua;;"
export LUA_CPATH="$BUILDCLUA/?.so;;"

LOGDIR=/hostlab/logs/`hostname`
#LOGDIR=/tmp


