#
# $Id: Makefile $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2013 cisco Systems, Inc.
#
# Created:       Tue Apr  9 14:04:26 2013 mstenber
# Last modified: Tue Nov 12 09:30:54 2013 mstenber
# Edit time:     7 min
#
#

# By default, create OWRT-using templates
CASEARGS=--replace-template bird=obird

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

# Utility targets which remake + start topologies

# bird7 = OWRT home router nodes
# rebuild-bird7 = bird7 with fresh rebuilt OWRT image as base
# debian-bird7 = OWRT home router nodes

bird7: clean
	python util/case2lab.py $(CASEARGS) bird7
	(cd lab/bird7 && lstart -p7)

rebuild-bird7: clean
	make -C ../openwrt
	python util/case2lab.py $(CASEARGS) bird7
	(cd lab/bird7 && lstart -p7)

debian-bird7: clean
	python util/case2lab.py bird7
	(cd lab/bird7 && lstart -p7)
