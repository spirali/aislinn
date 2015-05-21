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

from base.arc import Arc, ArcData
from context import Context
from event import MatchEvent
from state import State

import logging


class ErrorFound(Exception):
    pass


class GlobalContext:

    def __init__(self, generator, node, gstate):
        self.generator = generator
        self.node = node
        self.gstate = gstate
        self.contexts = [ None ] * generator.process_count
        self.events = []
        self.data = []

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

    def add_error_message(self, error_message):
        self.generator.add_error_message(error_message)

    def add_error_and_throw(self, error_message):
        self.add_error_message(error_message)
        raise ErrorFound()

    def make_node(self):
        self.save_states()
        node = self.generator.add_node(self.node, self.gstate)
        arc = Arc(node, self.events, self.get_compact_data())
        self.node.add_arc(arc)
        self.node = node
        self.events = None
        self.data = None
        self.gstate = None

    def make_fail_node(self):
        if not self.events and not self.data:
            # There is no visible change, so no new node is made
            return
        node = self.generator.add_node(self.node, self.gstate, do_hash=False)
        arc = Arc(node, self.events, self.get_compact_data())
        self.node.add_arc(arc)
        self.node = node

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
        return [ ArcData(key[0], key[1], key[0].compact_data(data)) for key, data in streams.items() ]

    def find_deterministic_match(self):
        for state in self.gstate.states:
            match = state.find_deterministic_match()
            if match:
                return match
        return None

    def find_nondeterministic_matches(self):
        results = []
        for state in self.gstate.states:
            results.extend(state.find_nondeterministic_matches())
        return results

    def apply_matching(self, matching):
        logging.debug("Apply matching: %s", matching)
        source_pid, s, target_pid, r = matching
        self.add_event(MatchEvent(source_pid, target_pid))
        # Receive has to be handled FIRST, otherwise buffer could be freed
        self.gstate.states[target_pid].finish_receive_request(
                r, s.comm.group.pid_to_rank(source_pid), s.tag, s.vg_buffer)
        self.gstate.states[source_pid].finish_send_request(s)

    def is_running(self, pid):
        context = self.contexts[pid]
        return context and context.controller.running
