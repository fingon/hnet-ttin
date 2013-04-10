#
# $Id: Makefile $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2013 cisco Systems, Inc.
#
# Created:       Tue Apr  9 14:04:26 2013 mstenber
# Last modified: Wed Apr 10 14:02:36 2013 mstenber
# Edit time:     1 min
#
#

# By default, create OWRT-using templates
CASEARGS=--replace-template bird=obird

build: lab/.all

lab/.all:
	python util/case2lab.py $(CASEARGS)
	touch lab/.all

lab/%:
	python util/case2lab.py $(CASEARGS) bird=obird $*

clean:
	vclean --clean-all
	rm -rf lab
