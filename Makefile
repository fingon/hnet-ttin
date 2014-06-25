#
# $Id: Makefile $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2013 cisco Systems, Inc.
#
# Created:       Tue Apr  9 14:04:26 2013 mstenber
# Last modified: Wed Jun 25 15:12:23 2014 mstenber
# Edit time:     12 min
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

lab/%/lab.conf:
	python util/case2lab.py $(CASEARGS) $*

lab/%.neato: lab/%/lab.conf
	util/lab2dot.py < lab/$*/lab.conf > lab/$*.neato

lab/%.svg: lab/%.neato
	neato -Tsvg < lab/$*.neato > lab/$*.svg

clean:
	vclean --clean-all
	rm -rf lab

