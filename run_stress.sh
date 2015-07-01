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
# Last modified: Wed Jul  1 12:51:42 2015 mstenber
# Edit time:     8 min
#

# Minor utility script which runs the full topology tests 5 times, and
# stores the logs.

DIRNAME=${1:-stress}-`date +'%y-%m-%d'`
NOSETESTS=`which nosetests3` || NOSETESTS=`which nosetests` || exit

mkdir -p $DIRNAME
for RUN in 1 2 3 4 5
do
    $NOSETESTS util/test_topo.py 2>&1 | tee $DIRNAME/log$RUN.txt
done

# these are done elsewhere; the stress-* should be moved to safe
# location anyway from here..
#util/stress2svg.py stress-* > ~/x/stress.svg
