#!/usr/bin/env python
# -*-Python-*-
#
# $Id: pprinter.py,v 1.3 2007-12-10 06:28:46 mstenber Exp $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Created:       Tue Nov 18 20:46:48 2003 mstenber
# Last modified: Wed Jul  4 12:29:56 2012 mstenber
# Edit time:     16 min
#
"""

PrettyPrinter and subclasses.

"""

C_INDENT_DEPTH=4

import string

class PrettyPrinter:
    """
    PrettyPrinter provides abstract way of outputting to a filehandle,
    with space-based indentation if need be.
    """
    def __init__(self, f, multiplier=C_INDENT_DEPTH):
        self.ofs = 0
        self.f = f
        self.multiplier = multiplier
    def __call__(self, s):
        for lineStub in string.split(s, '\n'):
            self.line(lineStub)
    def addLine(self, line):
        self.f.write(line)
    def line(self, s, indentOfs=0):
        s = string.rstrip(s)
        if '\n' in s:
            self(s)
            return
        i = self.ofs + indentOfs
        s = ' ' * (i * self.multiplier) + s + '\n'
        self.addLine(s)
    def indent(self, indentOfs=1):
        self.ofs = self.ofs + indentOfs
    def dedent(self, indentOfs=1):
        self.indent(-indentOfs)


class DelayedPrettyPrinterLines:
    def __init__(self, f):
        self.lines = []
        self.f = f
    def __del__(self):
        #print '*GC DPPL*'
        if self.lines:
            self.f.write(string.join(self.lines, ''))
    def __repr__(self):
        return '<%s instance %s>' % (self.__class__.__name__, {'f': self.f, 'lines': self.lines})

class DelayedPrettyPrinter(PrettyPrinter):
    """ DelayedPrettyPrinter is a PrettyPrinter which actually creates
    it's output at the time when it goes out of scope. This allows for
    delayed addition to any part of the prettyprinter, via means of
    bookmark() interface.  """
    def __init__(self, *args, **kwargs):
        apply(PrettyPrinter.__init__, (self,)+args, kwargs)
        self.bookmarks = []
        self.lines = DelayedPrettyPrinterLines(self.f)
    def addLine(self, s):
        self.getLines().append(s)
    def bookmark(self):
        """ This call returns a new DelayedPrettyPrinterBookmark
        positioned at current position. It can be used to insert data
        to current position, while the normal insertion continues at
        the end. """
        e = DelayedPrettyPrinterBookmark(self)
        self.bookmarks.append(e)
        return e
    def getLines(self):
        return self.lines.lines

class DelayedPrettyPrinterBookmark(DelayedPrettyPrinter):
    def __init__(self, p):
        # base class
        self.ofs = p.ofs
        # no self.f
        self.multiplier = p.multiplier

        # subclass
        self.lines = p.lines
        self.bookmarks = p.bookmarks

        # other ('writing position')
        self.i = len(self.lines.lines)

    def addLine(self, s):
        self.lines.lines.insert(self.i, s)
        self.i = self.i + 1
        # Then, find all fellow bookmarks that share the bookmark list
        # and update their positions accordingly..
        for bm in self.bookmarks:
            if bm.i >= self.i and bm is not self:
                bm.i = bm.i + 1
    def bookmark(self):
        e = DelayedPrettyPrinter.bookmark(self)
        e.i = self.i
        return e

