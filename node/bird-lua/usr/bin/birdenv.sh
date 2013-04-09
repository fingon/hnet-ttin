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
# Last modified: Thu Feb  7 14:00:24 2013 mstenber
# Edit time:     0 min
#

BIRD=/hosthome/uml/bird

export LUA_PATH="$BIRD/lua/?.lua;$BIRD/lua/thirdparty/?.lua;$BIRD/luarocks/share/lua/5.1/?.lua;$BIRD/?/init.lua;$BIRD/?.lua;;"
export LUA_CPATH="$BIRD/luarocks/lib/lua/5.1/?.so;;;"

LOGDIR=/hostlab/logs/`hostname`
#LOGDIR=/tmp

