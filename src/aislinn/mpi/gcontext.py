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

from context import Context
from state import State
from base.node import Arc

from base.stream import StreamChunk

class GlobalContext:

    def __init__(self, generator, node, gstate):
        self.generator = generator
        self.node = node
        self.gstate = gstate
        self.contexts = [ None ] * generator.process_count
        self.events = []
        self.stream_data = []

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

    def make_node(self):
        self.save_states()
        node = self.generator.add_node(self.node, self.gstate)
        arc = Arc(node, self.events, self.get_compact_stream_chunks())
        self.node.add_arc(arc)
        self.node = node
        self.events = None
        self.stream_data = None
        self.state = None
        self.gstate = None

    def make_fail_node(self):
        if not self.events and not self.stream_data:
            # There is no visible change, so no new node is made
            return
        node = self.generator.add_node(self.node, self.gstate, do_hash=False)
        arc = Arc(node, self.events, self.get_compact_stream_chunks())
        self.node.add_arc(arc)
        self.node = node

    def add_event(self, event):
        self.events.append(event)

    def add_stream_chunk(self, stream_name, pid, data):
        self.stream_data.append(((stream_name, pid), data))

    def get_compact_stream_chunks(self):
        if not self.stream_data:
            return None
        streams = {}
        for key, data in self.stream_data:
            lst = streams.get(key)
            if lst is None:
                lst = []
                streams[key] = lst
            lst.append(data)
        return [ StreamChunk(key[0], key[1], "".join(streams[key]))
                 for key in streams ]
