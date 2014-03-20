#
# $Id: Makefile $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2013 cisco Systems, Inc.
#
# Created:       Tue Apr  9 14:04:26 2013 mstenber
# Last modified: Thu Mar 20 12:02:54 2014 mstenber
# Edit time:     8 min
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

# Utility targets which remake + start topologies

# bird7 = OWRT home router nodes
# rebuild-bird7 = bird7 with fresh rebuilt OWRT image as base

# dbird7 = OWRT home router nodes (debug on)
# rebuild-dbird7 = bird7 with fresh rebuilt OWRT image as base (debug on)

# debian-bird7 = Debian home router nodes

bird7: clean
	python util/case2lab.py $(CASEARGS) bird7
	(cd lab/bird7 && lstart -p7)

rebuild-bird7: clean
	make -C ../openwrt
	python util/case2lab.py $(CASEARGS) bird7
	(cd lab/bird7 && lstart -p7)

dbird7: clean
	python util/case2lab.py $(CASEARGS_DEBUG) bird7
	(cd lab/bird7 && lstart -p7)

rebuild-dbird7: clean
	make -C ../openwrt
	python util/case2lab.py $(CASEARGS_DEBUG) bird7
	(cd lab/bird7 && lstart -p7)

debian-bird7: clean
	python util/case2lab.py bird7
	(cd lab/bird7 && lstart -p7)
