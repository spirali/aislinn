#
#    Copyright (C) 2014, 2015 Stanislav Bohm
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
#    along with Aislinn.  If not, see <http://www.gnu.org/licenses/>.
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

    @property
    def mpi_calls_count(self):
        count = 0
        for node in self.all_nodes():
            for arc in node.arcs:
                for event in arc.events:
                    if event.call_event:
                        count += 1
        return count

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

    def all_final_nodes(self):
        for node in self.all_nodes():
            if not node.arcs:
                yield node

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

    def arc_data_to_node(self, node, last_arc, name, pid):
        arcs = self.arcs_to_node(node)
        if last_arc:
            arcs.append(last_arc)
        return filter(None, (a.get_data(name, pid)
                             for a in arcs))

    def stream_to_node(self, node, last_arc, name, pid):
        return "".join(data.value
                       for data in self.arc_data_to_node(
                           node, last_arc, name, pid))

    def depth_first_search_with_arcs(self):
        stack = [ self.initial_node ]
        arcs = [ -1 ]
        stack_set = set(stack)
        visited = set(stack)

        while stack:
            s = stack[-1]
            c = arcs[-1] + 1
            if len(s.arcs) == c:
                stack_set.remove(stack.pop())
                arcs.pop()
                continue
            arcs[-1] += 1
            arc = s.arcs[c]

            node = arc.node
            v = node in visited
            if v:
                is_cycle = node in stack_set
            else:
                is_cycle = False
            yield s, arc, v, is_cycle
            if not v:
                visited.add(node)
                stack.append(node)
                stack_set.add(node)
                arcs.append(-1)

    def tree_reduce(self, reduce_op, arc_value, is_visible, leaf_value):
        assert self.initial_node
        stack = [ self.initial_node ]
        stack_set = set(stack)
        stack_arcs = [ 0 ]
        visited = {}
        while stack:
            node = stack[-1]
            a = stack_arcs[-1]
            if a == len(node.arcs):
                stack_set.remove(node)
                stack.pop()
                stack_arcs.pop()
                if not node.arcs:
                    visited[node] = leaf_value
                else:
                    visited[node] = reduce_op(arc_value(a, visited[a.node]) for a in node.arcs)
            else:
                stack_arcs[-1] += 1
                arc = node.arcs[a]
                if arc.node in stack_set:
                    # Cycle detected
                    if is_visible(arc):
                        return None
                    i = stack.index(arc.node)
                    for n, j in zip(stack[i:], stack_arcs[i:]):
                        if is_visible(n.arcs[j-1]):
                            return None
                    visited[arc.node] = frozenset()
                    # Invisible cycle
                elif arc.node not in visited:
                    stack.append(arc.node)
                    stack_set.add(arc.node)
                    stack_arcs.append(0)
        return visited[self.initial_node]

    def get_all_outputs(self, name, pid, limit=None, init=""):
        def arc_value(arc, node_value):
            data = arc.get_data(name, pid)
            if not data or not data.value:
                return node_value
            return frozenset(data.value + v for v in node_value)

        def arc_value_list(arc, node_value):
            value = None
            for p in pid:
                data = arc.get_data(name, p)
                if not data or not data.value:
                    continue
                if value is None:
                    value = data.value
                else:
                    value += data.value
            if value is None:
                return node_value
            else:
                return frozenset(value + v for v in node_value)

        def is_visible(arc):
            return bool(arc.get_data(name, pid))

        def reduce_op(values):
            result = frozenset.union(*values)
            if limit is None or len(result) <= limit:
                return result
            else:
                r = list(result)
                r.sort()
                return frozenset(r[:limit])
        return self.tree_reduce(reduce_op,
                                arc_value if not isinstance(pid, list)
                                          else arc_value_list,
                                is_visible,
                                frozenset((init,)))

    def get_outputs_count(self, stream_name, pid, upto):
        class TooManyOutputs(Exception):
            pass
        def arc_value(arc, node_value):
            chunk = arc.get_data(stream_name, pid)
            if not chunk or not chunk.value:
                return node_value

            return frozenset(chunk.value + v for v in node_value)

        def is_visible(arc):
            return bool(arc.get_data(stream_name, pid))

        def reduce_op(values):
            result = frozenset.union(*values)
            if len(result) <= upto:
                return result
            else:
                raise TooManyOutputs()
        try:
            outputs = self.tree_reduce(reduce_op,
                                       arc_value,
                                       is_visible,
                                       frozenset(("",)))
            if outputs is None:
                return None
            return len(outputs)
        except TooManyOutputs:
            return None

    def inject_indegree(self):
        for node in self.all_nodes():
            for arc in node.arcs:
                arc.node.indegree += 1

    def inject_dfs_indegree(self):
        for node, arc, visited, is_cycle \
                in self.depth_first_search_with_arcs():
            if not is_cycle:
                arc.node.indegree += 1

    def reconstruct_path(self, events):
        path = []
        node = self.initial_node
        events = list(events)
        while events:
            p, found = self.find_path_to_events(node, events)
            path.extend(p)
            for e in found:
                events.remove(e)
            node = path[-1].node
        return path

    def find_path_to_events(self, node, events):
        queue = [ node ]
        visited = { node: [] }
        found = []
        while queue:
            node = queue.pop()
            for arc in node.arcs:
                for e in events:
                    if e in arc.events:
                        found.append(e)
                if found:
                    return visited[node] + [arc], found
            if arc.node not in visited:
                path = visited[node][:]
                path.append(arc)
                visited[arc.node] = path
                queue.append(arc.node)
        assert 0, "Events not found"
