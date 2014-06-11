#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: stress2svg.py $
#
# Author: Markus Stenberg <mstenber@cisco.com>
#
# Copyright (c) 2014 cisco Systems, Inc.
#
# Created:       Wed Jun 11 12:57:29 2014 mstenber
# Last modified: Wed Jun 11 13:40:29 2014 mstenber
# Edit time:     14 min
#
"""

Produce SVG graph out of (historic) stress test results.

"""

import pygal
from pygal.style import Style
import nosefails
import glob
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('directory',
                nargs='+',
                help='Log file directory to parse')
args = ap.parse_args()

results = list(nosefails.parse_logs(*glob.glob('%s/log*.txt' % dir)) for dir in args.directory)

style = Style(colors=('#00ff00', '#00aa00', '#ff4000', '#ff0000'))
c = pygal.StackedBar(style=style)
c.title = 'Stress test results over time'
c.add('success', [r.cases_ok() for r in results])
c.add('flaky', [r.cases_fail('flaky') for r in results])
c.add('inconsistent', [r.cases_fail('inconsistent') for r in results])
c.add('broken', [r.cases_fail('broken') for r in results])
import sys, os
os.write(sys.stdout.fileno(), c.render())

