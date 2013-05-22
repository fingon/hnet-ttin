#!/bin/sh
#-*-sh-*-
#
# $Id: skvtool.sh $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
#  Copyright (c) 2012 Markus Stenberg
#       All rights reserved
#
# Created:       Tue Oct  9 10:46:31 2012 mstenber
# Last modified: Wed May 22 14:23:32 2013 mstenber
# Edit time:     3 min
#

. /usr/bin/luaenv.sh

lua $CORE/skvtool.lua $*
