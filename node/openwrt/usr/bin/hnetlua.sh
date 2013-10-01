#!/bin/sh  -ue
#-*-sh-*-
#
# $Id: hnetlua.sh $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2013 cisco Systems, Inc.
#
# Created:       Tue Oct  1 15:05:24 2013 mstenber
# Last modified: Tue Oct  1 15:14:02 2013 mstenber
# Edit time:     2 min
#

CMD=$1
shift
HNET=/hosthome/hnet
BUILD=$HNET/build
CORE=$HNET/component/core
LUADIR=$CORE
BUILDLUA=$BUILD/share/lua/5.1
export LUA_PATH="$CORE/?.lua;$CORE/thirdparty/?.lua;$BUILDLUA/?.lua;$BUILDLUA/?/init.lua;;"
lua $LUADIR/$CMD $*
