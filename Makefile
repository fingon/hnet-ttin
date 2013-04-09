#
# $Id: Makefile $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2013 cisco Systems, Inc.
#
# Created:       Tue Apr  9 14:04:26 2013 mstenber
# Last modified: Tue Apr  9 15:18:23 2013 mstenber
# Edit time:     0 min
#
#

# By default, create OWRT-using templates
build:
	python util/case2lab.py --replace-template bird=obird

clean:
	vclean --clean-all
	rm -rf lab
