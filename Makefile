#
# $Id: Makefile $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2013 cisco Systems, Inc.
#
# Created:       Tue Apr  9 14:04:26 2013 mstenber
# Last modified: Wed Jun 25 14:49:37 2014 mstenber
# Edit time:     9 min
#
#

# By default, create OWRT-using templates
CASEARGS=--replace-template bird=obird
CASEARGS_DEBUG=--replace-template bird=obird-debug

build: lab/.all

debian: lab/.all
	python util/case2lab.py
	touch lab/.all

lab/.all:
	python util/case2lab.py $(CASEARGS)
	touch lab/.all

lab/%:
	python util/case2lab.py $(CASEARGS) bird=obird $*

clean:
	vclean --clean-all
	rm -rf lab

