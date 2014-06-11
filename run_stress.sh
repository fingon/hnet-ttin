#!/bin/bash -ue
#-*-sh-*-
#
# $Id: run_stress.sh $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Fri Mar 28 13:15:39 2014 mstenber
# Last modified: Wed Jun 11 14:09:22 2014 mstenber
# Edit time:     4 min
#

# Minor utility script which runs the full topology tests 5 times, and
# stores the logs.

DIRNAME=stress-`date +'%m-%d'`

mkdir -p $DIRNAME
for RUN in 1 2 3 4 5
do
    nosetests util/test_topo.py 2>&1 | tee $DIRNAME/log$RUN.txt
done
util/stress2svg.py stress-* > ~/x/stress.svg
