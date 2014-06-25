#!/usr/bin/env python
# -*-Python-*-
#------------------------------------------------------
# dot.py
#
# Copyright (c) 2014 by cisco Systems, Inc.
# All rights reserved.
#------------------------------------------------------
"""

Yet Another Graphviz Python Backend (...)

"""

class DotGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.aliases= {}
    def alias(self, name, alias):
        self.aliases[alias] = name
    def node(self, name, **kwargs):
        self.nodes[name] = kwargs
        return name
    def transition(self, node1, node2, **attributes):
        self.edges[node1,node2] = attributes
    def dumpData(self):
        def _dump(h):
            r = ", ".join(map(lambda (k, v):'%s=%s' %(k,v), h.items()))
            if r:
                r = '[%s]' % r
            return r
        l = []
        for nodeName, v in self.nodes.items():
            attrs = _dump(v)
            l.append('"%(nodeName)s" %(attrs)s;' % locals())
        for (src, dst), v in self.edges.items():
            src = self.aliases.get(src, src)
            dst = self.aliases.get(dst, dst)
            attrs = _dump(v)
            l.append('"%(src)s" -> "%(dst)s" %(attrs)s;' % locals())
        return "\n".join(l)
    def dump(self):
        return """
digraph dummy {
%s
}""" % self.dumpData()


if __name__ == '__main__':
    dg = DotGraph()
    triangle = dg.node('triangle', shape='triangle')
    square = 'square'
    dg.transition(triangle, square)
    print dg.dump()
