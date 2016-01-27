#
#    Copyright (C) 2015 Stanislav Bohm
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

import base.utils as utils
from request import Request
import copy
import logging
import errormsg


class DeadlockFound(Exception):

    def __init__(self, marks):
        self.marks = marks


class NdsyncChecker:

    def __init__(self, generator, statespace):
        self.generator = generator
        self.statespace = statespace

        self.markings = {}
        self.queue = None

    def add_marking(self, node, marking):
        markings = self.markings.get(node)
        if markings is None:
            self.markings[node] = [marking]
        elif marking not in markings:
            for m in markings:
                if marking.is_covered_by(m):
                    return
            """ is_covered_by is now symetric so other direction is not necessary
            for i, m in enumerate(markings):
                if m.is_covered_by(marking):
                    markings[i] = marking
                    return
            """
            markings.append(marking)

    def run(self):
        initial_node = self.statespace.initial_node
        # If there are not events in initialization phase,
        # go directly to next node.
        # It ensures that every arc has at least one event
        if not initial_node.arcs[0].events:
            initial_node = initial_node.arcs[0].node

        self.markings[initial_node] = [Marking(self)]
        self.queue = [initial_node]
        try:
            while self.queue:
                node = self.queue.pop()
                markings = self.markings.pop(node)
                self.process_node(node, markings)
        except DeadlockFound as e:
            return self.reconstruct_deadlock(e.marks)
        assert not self.markings
        return None

    def replay_path(self, path, synchronous_marks):
        marking = Marking(self)
        result = []
        for arc in path:
            for e in arc.events:
                marks = marking.get_event_marks(e)
                marking.process_event(e)
                difference = marks - synchronous_marks
                if difference:
                    marking.remove_marks_and_cleanup(difference)
                    marks = marks.intersection(synchronous_marks)
                if not marks:
                    result.append(e)
        return result, marking

    def reconstruct_deadlock(self, marks):
        events = [m.event for m in marks]
        path = self.statespace.reconstruct_path(events)
        pruned_events, marking = self.replay_path(path, marks)
        pids = [e.pid for e in pruned_events if e.name == "Exit"]
        active_pids = list(set(range(len(marking.process_marks))) - set(pids))
        active_pids.sort()
        message = errormsg.Deadlock(None, active_pids=active_pids)
        message.events = pruned_events
        for e in events:
            e.ndsync = True
        return message

    def process_node(self, node, markings):
        if not node.arcs:
            for marking in markings:
                marks = frozenset(marking.terminate_marks.keys())
                assert not marking.active_marks
                assert not marking.finished_marks
                for m in marking.process_marks:
                    assert marks.issuperset(m)
                if marks:
                    logging.debug("ndsync: deadlock type1 found")
                    raise DeadlockFound(marks)
            return

        for marking in markings:
            if len(node.arcs) > 1:
                event_marks = [
                    marking.get_event_marks(a.events[0])
                    for a in node.arcs]
                if all(event_marks):
                    logging.debug("ndsync: deadlock type2 found")
                    raise DeadlockFound(frozenset().union(*event_marks))
            else:
                event_marks = None
            for i, arc in enumerate(node.arcs):
                m = marking.copy()
                if event_marks and event_marks[i]:
                    m.remove_marks_and_cleanup(event_marks[i])
                for event in arc.events:
                    m.process_event(event)
                if arc.node.indegree > 0:
                    self.add_marking(arc.node, m)

        for arc in node.arcs:
            n = arc.node
            n.indegree -= 1
            # negative indegree means cycle, we are not ignoreing cycles
            if n.indegree == 0:
                assert n.indegree == 0
                self.queue.append(n)


def get_request_type(request_id):
    return request_id % Request.TYPES_COUNT


class CollectiveOperation(utils.EqMixin):

    def __init__(self, comm_id, cc_id, size, mark, marks):
        self.comm_id = comm_id
        self.cc_id = cc_id
        self.size = size
        self.marks = {mark: marks}

    def add_marks(self, mark, marks):
        c = copy.copy(self)
        c.marks = copy.copy(c.marks)
        c.marks[mark] = marks
        return c

    def remove_marks(self, marks):
        c = copy.copy(self)
        c.marks = {event: m - marks for event, m in c.marks.items()}
        return c

    def update(self, other):
        c = copy.copy(self)
        for m in self.marks:
            c.marks[m] = c.marks[m].union(other.marks[m])
        return c

    def is_finished(self):
        return self.size == len(self.marks)

    def __repr__(self):
        return "<CC comm_id={0.comm_id} cc_id={0.cc_id} marks={0.marks}>" \
            .format(self)


class Mark:

    def __init__(self, event, request_id):
        self.event = event
        self.request_id = request_id

    @property
    def pid(self):
        return self.event.pid

    def __hash__(self):
        return hash(self.event) ^ self.request_id

    def __eq__(self, other):
        return (isinstance(other, Mark) and
                self.event == other.event and
                self.request_id == other.request_id)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "<M {0.event} id={0.request_id}>".format(self)


class Marking(utils.EqMixin):

    def __init__(self, checker):
        process_count = checker.generator.process_count
        self.process_marks = [frozenset()
                              for i in xrange(process_count)]
        self.active_marks = {}
        self.finished_marks = {}
        self.ssend_marks = {}  # Active std sends
        self.terminate_marks = {}

        self.collectives = ()  # Copy on write

    def copy(self):
        c = copy.copy(self)
        c.process_marks = copy.copy(self.process_marks)
        c.active_marks = copy.copy(self.active_marks)
        c.finished_marks = copy.copy(self.finished_marks)
        c.ssend_marks = copy.copy(self.ssend_marks)
        c.terminate_marks = copy.copy(self.terminate_marks)
        return c

    def get_event_marks(self, event):
        if event.name == "Match":
            source = self.active_marks[event.source_id]
            target = self.active_marks[event.target_id]
            return source.union(target)
        elif event.name == "Continue":
            marks = self.process_marks[event.pid]
            for request_id in event.request_ids:
                if get_request_type(request_id) == Request.TYPE_SEND_STD:
                    e = self.ssend_marks.get(request_id)
                    if e:
                        marks = marks.union(frozenset((e,)))
                marks = marks.union(self.finished_marks[request_id])
            return marks
        else:
            return self.process_marks[event.pid]

    def is_covered_by(self, marking):
        if len(self.terminate_marks) != len(marking.terminate_marks):
            # markings with terminate_marks are not handled yet
            return False

        def apply_mapping(s):
            return frozenset(mapping[m] for m in s)

        def check_dicts(d1, d2):
            for key in d1:
                if (apply_mapping(d1[key]) != d2[key]):
                    return False
            return True

        def check_mark_dicts(d1, d2):
            for key in d1:
                if apply_mapping(d1[key]) != d2[mapping[key]]:
                    return False
            return True

        def mark_pid(mark):
            return mark.pid

        def pre_check_fn(m, v1, v2):
            return len(self.terminate_marks[v1]) == \
                len(marking.terminate_marks[v2]),

        assert len(self.ssend_marks) == len(marking.ssend_marks)
        mapping = {}  # mapping of markigs between "self" and "marking"

        # compose mapping

        for request_id in self.ssend_marks:
            mapping[self.ssend_marks[request_id]] = \
                marking.ssend_marks[request_id]

        for c in self.collectives:
            c2 = marking.find_collective(c.comm_id, c.cc_id)
            m1 = c.marks.keys()
            m1.sort(key=mark_pid)
            m2 = c2.marks.keys()
            m2.sort(key=mark_pid)
            mapping.update(zip(m1, m2))

        for mapping in utils.build_equivalence(
                self.terminate_marks.keys(),
                marking.terminate_marks.keys(),
                pre_check_fn,
                mapping):
            # check mapping
            for m1, m2 in zip(self.process_marks, marking.process_marks):
                if apply_mapping(m1) != m2:
                    continue

            if not check_dicts(self.active_marks, marking.active_marks):
                continue
            if not check_dicts(self.finished_marks, marking.finished_marks):
                continue

            for c in self.collectives:
                c2 = marking.find_collective(c.comm_id, c.cc_id)
                if not check_mark_dicts(c.marks, c2.marks):
                    continue
            if not check_mark_dicts(self.terminate_marks,
                                    marking.terminate_marks):
                continue
            return True
        return False

    def find_collective(self, comm_id, cc_id):
        for c in self.collectives:
            if comm_id == c.comm_id and cc_id == c.cc_id:
                return c

    def prev_of_marks(self, marks):
        prev = None
        next = marks
        while prev != next:
            n = frozenset().union(
                *filter(None, (self.terminate_marks.get(m) for m in next)))
            prev = next
            next = next.union(n)
        return next

    def remove_marks_and_cleanup(self, marks):
        self.remove_marks(marks)
        while True:
            for mark, marks in self.terminate_marks.items():
                if not marks:
                    self.remove_marks(frozenset((mark,)))
                    break
            else:
                return

    def match(self, mark, marks):
        if marks:
            self.terminate_marks[mark] = marks
        else:
            self.remove_marks_and_cleanup(frozenset((mark,)))

    def add_collective(self, event, request_id):
        mark = Mark(event, request_id)
        marks = self.process_marks[event.pid]
        self.finished_marks[request_id] = marks.union(frozenset((mark,)))
        comm_id, cc_id, size = event.cc
        c = self.find_collective(comm_id, cc_id)
        collectives = list(self.collectives)
        if c:
            index = collectives.index(c)
            c = c.add_marks(mark, marks)
            collectives[index] = c
        else:
            c = CollectiveOperation(comm_id, cc_id, size, mark, marks)
            collectives.append(c)

        if c.is_finished():
            collectives.remove(c)
            self.collectives = tuple(collectives)
            all_marks = frozenset.union(*c.marks.values())
            for mark in c.marks:
                self.match(mark, all_marks)
        else:
            self.collectives = tuple(collectives)

    def process_new_request(self, event, request_id):
        t = get_request_type(request_id)
        if t == Request.TYPE_COLLECTIVE:
            self.add_collective(event, request_id)
            return
        self.active_marks[request_id] = self.process_marks[event.pid]
        if t == Request.TYPE_SEND_EAGER:
            self.finished_marks[request_id] = self.process_marks[event.pid]
        if t == Request.TYPE_SEND_STD:
            self.finished_marks[request_id] = self.process_marks[event.pid]
            mark = Mark(event, request_id)
            self.ssend_marks[request_id] = mark

    def process_event(self, event):
        if event.new_request:
            if isinstance(event.new_request, list):
                for request_id in event.new_request:
                    self.process_new_request(event, request_id)
            else:
                self.process_new_request(event, event.new_request)
        elif event.name == "Match":
            source = self.active_marks.pop(event.source_id)
            target = self.active_marks.pop(event.target_id)
            new = source.union(target)
            self.finished_marks[event.target_id] = new
            t = get_request_type(event.source_id)
            if t == Request.TYPE_SEND_RENDEZVOUS:
                self.finished_marks[event.source_id] = new
            elif t == Request.TYPE_SEND_STD:
                if event.source_id in self.finished_marks:
                    self.finished_marks[event.source_id] = \
                        self.finished_marks[event.source_id].union(new)
                    event = self.ssend_marks[event.source_id]
                else:
                    event = self.ssend_marks.pop(event.source_id, None)
                if event:
                    self.match(event, target)
        elif event.name == "Continue":
            for request_id in event.request_ids:
                marks = self.finished_marks.pop(request_id, None)
                t = get_request_type(request_id)
                if t == Request.TYPE_COLLECTIVE:
                    self.add_process_marks(event.pid, marks)
                elif t == Request.TYPE_SEND_STD:
                    if request_id in self.active_marks:
                        mark = self.ssend_marks.get(request_id)
                    else:
                        # mark can be None if ssend was already matched
                        # and cleaned up by match
                        mark = self.ssend_marks.pop(request_id, None)
                    if mark:
                        marks = marks.union(frozenset((mark,)))
                    self.add_process_marks(event.pid, marks)
                else:
                    self.add_process_marks(event.pid, marks)

    def add_process_marks(self, pid, marks):
        self.process_marks[pid] = self.process_marks[pid].union(marks)

    def remove_marks(self, marks):
        if marks:
            self.process_marks = [m - marks for m in self.process_marks]
            self.active_marks = {k: m - marks
                                 for k, m in self.active_marks.items()}
            self.finished_marks = {k: m - marks
                                   for k, m in self.finished_marks.items()}
            self.terminate_marks = {k: m - marks
                                    for k, m in self.terminate_marks.items()}

            self.collectives = tuple(c.remove_marks(marks)
                                     for c in self.collectives)
            for m in marks:
                if m in self.terminate_marks:
                    del self.terminate_marks[m]
                for k, v in self.ssend_marks.items():
                    if v == m:
                        del self.ssend_marks[k]

    def dump(self):
        print ">>>>>>> Marking", self, "<<<<<<<"
        for i, m in enumerate(self.process_marks):
            print "PID ", i, m
        print "arqs=", self.active_marks
        print "frqs=", self.finished_marks
        print "ssm=", self.ssend_marks
        print "tm="
        for m, n in self.terminate_marks.items():
            print m, ">>"
            for i in n:
                print "   ", i

        print "cc="
        for cc in self.collectives:
            print cc
