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

from base.arc import Arc, ArcData, COUNTER_MPICALLS
from context import Context
from event import MatchEvent
from state import State

import logging
import datetime


class ErrorFound(Exception):
    pass


class GlobalContext:

    init_time = None

    def __init__(self, worker, gstate):
        self.worker = worker
        self.gstate = gstate
        self.action = None

        self.contexts = [None] * worker.process_count
        self.events = []
        self.data = []

        #if generator.debug_arc_times:
        #    self.init_time = datetime.datetime.now()


    def get_context(self, pid):
        context = self.contexts[pid]
        if context is None:
            if self.gstate is not None:
                context = Context(self, self.gstate.states[pid])
            else:
                context = Context(self, None)
            self.contexts[pid] = context
        return context

    def prepare_context(self, pid):
        context = self.get_context(pid)
        if context.controller is None:
            context.restore_state()
        context.controller.make_buffers()
        return context

    def save_states(self):
        for context in self.contexts:
            if (context and context.controller and
                    context.state.status != State.StatusFinished):
                context.save_state_with_hash()

    def add_error_and_throw(self, error_message):
        self.worker.send_error_message(error_message)
        raise ErrorFound()

    """
    def make_node(self):
        self.save_states()
        node, is_new = self.generator.add_node(
            self.node, self.worker, self.gstate)
        arc = Arc(node, self.action, self.events, self.get_compact_data())

        if self.init_time:
            now = datetime.datetime.now()
            arc.time = (now - self.init_time).total_seconds()

        self.node.add_arc(arc)
        self.node = node
        self.events = None
        self.data = None
        self.contexts = None
        self.action = None

        # DEBUG
        arc.worker = self.worker.worker_id
        return is_new

    def add_to_queue(self, action, copy):
        assert not self.events
        gstate = self.gstate
        if copy:
            gstate = gstate.copy()
        else:
            self.gstate = None
        self.worker.add_to_queue(self.node, gstate, action)

    def make_fail_node(self):
        if not self.events and not self.data:
            # There is no visible change, so no new node is made
            return
        node, is_new = self.generator.add_node(
            self.node, self.worker, self.gstate, do_hash=False)
        arc = Arc(node, self.action, self.events, self.get_compact_data())
        self.node.add_arc(arc)
        self.node = node

        self.events = None
        self.data = None
        self.contexts = None
        self.action = None
    """

    def add_event(self, event):
        self.events.append(event)

    def add_data(self, name, pid, data):
        self.data.append(((name, pid), data))

    def get_compact_data(self):
        if not self.data:
            return None
        streams = {}
        for key, data in self.data:
            lst = streams.get(key)
            if lst is None:
                lst = []
                streams[key] = lst
            lst.append(data)
        data = [ArcData(key[0], key[1], key[0].compact_data(data))
                for key, data in streams.items()]
        if self.generator.profile:
            for pid in xrange(self.generator.process_count):
                value = len([e for e in self.events
                             if e.call_event and e.pid == pid])
                if value:
                    data.append(ArcData(COUNTER_MPICALLS, pid, value))
        return data

    def find_deterministic_match(self):
        for state in self.gstate.states:
            match = state.find_deterministic_match()
            if match:
                return match
        return None

    def apply_matching(self, matching):
        logging.debug("Apply matching: %s", matching)
        source_pid, s, target_pid, r = matching
        self.add_event(MatchEvent(s.id, r.id))
        # Receive has to be handled FIRST, otherwise buffer could be freed
        self.gstate.states[target_pid].finish_receive_request(
            r, s.comm.group.pid_to_rank(source_pid), s.tag, s.vg_buffer)
        self.gstate.states[source_pid].finish_send_request(s)

    def is_pid_running(self, pid):
        context = self.contexts[pid]
        return context and context.controller.running

    def is_running(self):
        for context in self.contexts:
            if context and context.controller.running:
                return True
        return False
