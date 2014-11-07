#
#    Copyright (C) 2014 Stanislav Bohm
#
#    This file is part of Aislinn.
#
#    Aislinn is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 of the License, or
#    (at your option) any later version.
#
#    Aislinn is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Kaira.  If not, see <http://www.gnu.org/licenses/>.
#


import itertools

class StateSpace:

    def __init__(self):
        self.nodes_without_hash = []
        self.nodes_with_hash = {}
        self.initial_node = None

    @property
    def nodes_count(self):
        return len(self.nodes_with_hash) + len(self.nodes_without_hash)

    def get_node_by_hash(self, hash):
        return self.nodes_with_hash.get(hash)

    def add_node(self, node):
        if node.hash is None:
            self.nodes_without_hash.append(node)
        else:
            self.nodes_with_hash[node.hash] = node

    def all_nodes(self):
        return itertools.chain(self.nodes_without_hash,
                               self.nodes_with_hash.values())

    def write_dot(self, filename):
        def _write_node(node):
            i = id(node)
            f.write("S{0} [label=\"{1}\"]\n".format(i, node.uid))
            for arc in node.arcs:
                f.write("S{0} -> S{1} [label=\"{2.label}\"]\n".format(
                    i, id(arc.node), arc))
        with open(filename, "w") as f:
            f.write("digraph X {\n")
            for node in self.all_nodes():
                _write_node(node)
            f.write("}\n")

    def write(self, filename):
        def _write_node(node):
            f.write("{0}\n".format(node.uid))
            for arc in node.arcs:
                f.write("\t{0} {1}\n".format(arc.node.uid, arc.label))
        with open(filename, "w") as f:
            f.write("{0}\n".format(self.initial_node.uid))
            for node in self.all_nodes():
                _write_node(node)

    def arcs_to_node(self, node):
        end = self.initial_node
        n = node
        arcs = []
        while n is not end:
            prev = n.prev
            for arc in prev.arcs:
                if arc.node is n:
                    arcs.append(arc)
                    n = prev
                    break
            else:
                raise Exception("Inconsistent nodes")
        arcs.reverse()
        return arcs

    def events_to_node(self, node, last_arc):
        arcs = self.arcs_to_node(node)
        if last_arc:
            arcs.append(last_arc)
        return list(itertools.chain.from_iterable(
            a.events for a in arcs))
