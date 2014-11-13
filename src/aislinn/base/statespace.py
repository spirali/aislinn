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
import os


class StreamNode:

    def __init__(self):
        self.childs = []
        self.end_of_path = False
        self.node = None
        self.cycle_arcs = None

    def find_or_create_child(self, data):
        if not data:
            return self
        for node_arc_data in self.childs:
            node, arc_data = node_arc_data
            if data[0] != arc_data[0]:
                continue
            if data == arc_data:
                return node
            prefix = os.path.commonprefix((arc_data, data))
            if len(prefix) == len(arc_data):
                return node.find_or_create_child(data[len(prefix):])
            split_node = StreamNode()
            node_arc_data[0] = split_node
            node_arc_data[1] = prefix
            split_node.childs.append([ node, arc_data[len(prefix):] ])
            if len(prefix) == len(data):
                return split_node
            new_node = StreamNode()
            split_node.childs.append([ new_node, data[len(prefix):] ])
            return new_node
        else:
            new_node = StreamNode()
            self.childs.append([new_node, data])
            return new_node

    def tree_reduce(self, reduce_op):
        stack = [ (self, False) ]
        visited = { self: None }
        while stack:
            snode, completed = stack.pop()
            if completed:
                visited[snode] = reduce_op(snode, (visited[s] for s, d in snode.childs))
            elif not snode.childs:
                visited[snode] = reduce_op(snode, ())
            else:
                stack.append((snode, True))
                for s, d in snode.childs:
                    if s not in visited:
                        visited[s] = None
                        stack.append((s, False))
        return visited[self]

    def tree_paths(self):
        stack = [ self ]
        childs = [ -1 ]

        while stack:
            s = stack[-1]
            c = childs[-1] + 1
            if len(s.childs) == c:
                stack.pop()
                childs.pop()
                if s.end_of_path:
                    yield stack, childs
                continue
            childs[-1] += 1
            stack.append(s.childs[c][0])
            childs.append(-1)

    @property
    def count_of_words(self):
        return self.tree_reduce(lambda n, values: sum(values, 1 if n.end_of_path else 0))

    @property
    def all_outputs(self):
        if not self.childs and self.end_of_path:
            return [ "" ]
        return ("".join(s.childs[i][1] for s, i in zip(stack, childs))
                for stack, childs in self.tree_paths())

    def __repr__(self):
        return "<StreamNode {0:x} childs={1}>".format(id(self), len(self.childs))


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
                f.write("S{0} -> S{1} [label=\"{2}\"]\n".format(
                    i, id(arc.node), arc.label))
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
        assert node is not None
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

    def stream_chunks_to_node(self, node, last_arc, stream_name, pid):
        arcs = self.arcs_to_node(node)
        if last_arc:
            arcs.append(last_arc)
        return filter(None, (a.get_stream_chunk(stream_name, pid)
                             for a in arcs))

    def stream_to_node(self, node, last_arc, stream_name, pid):
        return "".join(chunk.data
                       for chunk in self.stream_chunks_to_node(
                           node, last_arc, stream_name, pid))

    def depth_first_search_with_arcs(self):
        queue = [ [self.initial_node, False] ]
        queue_set = set((self.initial_node,))
        visited = set((self.initial_node,))
        while queue:
            node, completed = queue[-1]
            if completed:
                queue.pop()
                queue_set.remove(node)
                continue
            queue[-1][1] = True # completed = True
            for arc in node.arcs:
                if arc.node not in visited:
                    yield node, arc, False
                    visited.add(arc.node)
                    queue.append([arc.node, False])
                    queue_set.add(arc.node)
                else:
                    yield node, arc, arc.node in queue_set

    def get_stream_tree(self, stream_name, pid):
        root = StreamNode()
        mapping = { self.initial_node: root }

        if not self.initial_node.arcs:
            root.end_of_path = True
            return root

        for node, arc, is_cycle_arc in self.depth_first_search_with_arcs():
            snode = mapping[node]
            chunk = arc.get_stream_chunk(stream_name, pid)
            if is_cycle_arc:
                if snode == mapping[arc.node]:
                    continue # It is invisible cycle, so it is ok
                # TODO: Support for cyles
                return None
            else:
                if chunk:
                    snode = snode.find_or_create_child(chunk.data)
                mapping[arc.node] = snode
                if not arc.node.arcs:
                    snode.node = arc.node
                    snode.end_of_path = True
        return root
