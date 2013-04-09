#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: configdelta.py $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Created:       Wed Jun 27 14:12:57 2012 mstenber
# Last modified: Wed Jun 27 14:16:28 2012 mstenber
# Edit time:     3 min
#
"""

This is a minimalist .config delta tool - it shows stuff missing/added
from config file A to config file B.

"""

import re

config_re = re.compile('^(CONFIG.*)=(y|m)$').match

def read_config(filename):
    l = []
    for line in open(filename):
        m = config_re(line)
        if m is None:
            continue
        l.append(m.group(1))
    return l

def delta_config(c1, c2):
    s1 = set(c1)
    s2 = set(c2)
    m2 = list(s1.difference(s2))
    a2 = list(s2.difference(s1))
    m2.sort()
    a2.sort()
    for e in m2:
        print '-', e
    for e in a2:
        print '+', e

if __name__ == '__main__':
    import sys
    (f1, f2) = sys.argv[1:] # provide two .config files
    delta_config(read_config(f1), read_config(f2))

