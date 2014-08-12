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


import hashlib
from base.utils import EqMixin


class GlobalState(EqMixin):

    def __init__(self,
                 states,
                 send_protocol_thresholds,
                 collective_operations=None):
        self.states = tuple(states)
        self.collective_operations = collective_operations
        self.send_protocol_thresholds = send_protocol_thresholds

    def copy(self):
        states = [ state.copy() for state in self.states ]
        if self.collective_operations:
            collective_operations = [ op.copy() \
                                      for op in self.collective_operations ]
        else:
            collective_operations = None
        return GlobalState(
                states, self.send_protocol_thresholds, collective_operations)

    def dispose(self):
        for state in self.states:
            state.dispose()
        if self.collective_operations:
            for op in self.collective_operations:
                op.dispose()

    def get_state(self, rank):
        return self.states[rank]

    def compute_hash(self):
        for state in self.states:
            # If state is not hashed we cannot have a global hash
            if not state.is_hashable():
                return None
        hashthread = hashlib.md5()
        if self.send_protocol_thresholds:
            hashthread.update(str(self.send_protocol_thresholds))
        for state in self.states:
            state.compute_hash(hashthread)
        if self.collective_operations:
            for op in self.collective_operations:
                op.compute_hash(hashthread)
        return hashthread.hexdigest()

    def init_collective_operation(self, op, blocking, index):
        assert index <= len(self.collective_operations)
        if len(self.collective_operations) == index:
            self.collective_operations.append(op(self, blocking))

    def get_operation_by_cc_id(self, cc_id):
        for op in self.collective_operations:
            if op.cc_id == cc_id:
                return op

    def call_collective_operation(self, generator, state, op_class, blocking, args):
        if self.collective_operations is None:
            self.collective_operations = []
        cc_id = state.cc_id_counter
        op = self.get_operation_by_cc_id(cc_id)
        if op is not None:
            # TODO: Check compatability
            pass
        else:
            op = op_class(self, blocking, cc_id)
            self.collective_operations.append(op)
        state.inc_cc_id_counter()
        op.enter(generator, self, state, args)
        return cc_id

    def finish_collective_operation(self, op):
        self.collective_operations.remove(op)

    @property
    def process_count(self):
        return len(self.states)
