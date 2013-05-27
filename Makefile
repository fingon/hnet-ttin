#
# $Id: Makefile $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2013 cisco Systems, Inc.
#
# Created:       Tue Apr  9 14:04:26 2013 mstenber
# Last modified: Mon May 27 13:46:34 2013 mstenber
# Edit time:     4 min
#
#

# By default, create OWRT-using templates
CASEARGS=--replace-template bird=obird

build: lab/.all

debian: lab/.all
	python util/case2lab.py
	touch lab/.all

debian-bird7: clean
	python util/case2lab.py bird7
	(cd lab/bird7 && lstart)

lab/.all:
	python util/case2lab.py $(CASEARGS)
	touch lab/.all

lab/%:
	python util/case2lab.py $(CASEARGS) bird=obird $*

clean:
	vclean --clean-all
	rm -rf lab
