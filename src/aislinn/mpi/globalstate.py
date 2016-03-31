#
#    Copyright (C) 2014, 2015, 2016 Stanislav Bohm
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

from action import (ActionMatching,
                    ActionWaitAny,
                    ActionWaitSome,
                    ActionFlag0,
                    ActionProbePromise,
                    ActionTestAll)
import hashlib
from base.utils import EqMixin, power_set
from comm import Communicator, Group, make_comm_world
import copy
from state import State
import consts
import logging
import msgpack

class GlobalState(EqMixin):

    def __init__(self, process_count, loader=None):
        self.comm_world = make_comm_world(process_count)
        self.states = [State(self, i, None) for i in xrange(process_count)]
        self.collective_operations = None
        self.comm_id_counter = consts.MPI_COMM_USERDEF

    def serialize_to_list(self):
        lst = [state.serialize_to_list() for state in self.states]
        if self.collective_operations:
            lst.append(len(self.collective_operations))
            for op in self.collective_operations:
                op.serialize_to_list(lst)
        else:
            lst.append(None)
        return lst

    def copy(self):
        logging.debug("Copying gstate %s", self)
        gstate = copy.copy(self)
        gstate.states = [state.copy(gstate) for state in self.states]
        if self.collective_operations is not None:
            gstate.collective_operations = \
                [op.copy() for op in self.collective_operations]
        return gstate

    def transfer(self, transfer_context):
        logging.debug("Transfering gstate %s", self)
        gstate = copy.copy(self)
        gstate.states = [state.transfer(gstate, transfer_context)
                         for state in self.states]
        if self.collective_operations is not None:
            gstate.collective_operations = \
                [op.transfer(transfer_context)
                 for op in self.collective_operations]
        return gstate

    @property
    def process_count(self):
        return len(self.states)

    def dispose(self):
        logging.debug("Disposing %s", self)
        for state in self.states:
            state.dispose()
        if self.collective_operations:
            for op in self.collective_operations:
                op.dispose()
        self.states = None
        self.collective_operations = None

    def get_state(self, pid):
        return self.states[pid]

    def compute_hash(self):
        hashthread = hashlib.md5()
        hashthread.update(msgpack.dumps(self.serialize_to_list()))
        return hashthread.hexdigest()

    def init_collective_operation(self, op, blocking, index):
        assert index <= len(self.collective_operations)
        if len(self.collective_operations) == index:
            self.collective_operations.append(op(self, blocking))

    def get_operation_by_cc_id(self, comm_id, cc_id):
        for op in self.collective_operations:
            if op.cc_id == cc_id and op.comm_id == comm_id:
                return op

    def call_collective_operation(self,
                                  context,
                                  comm,
                                  op_class,
                                  blocking,
                                  args):
        assert context.gcontext.gstate is self
        if self.collective_operations is None:
            self.collective_operations = []
        cc_id = context.state.get_cc_id_counter(comm)
        op = self.get_operation_by_cc_id(comm.comm_id, cc_id)
        if op is not None and comm.comm_id != consts.MPI_COMM_SELF:
            op.check_compatability(context, op_class, blocking)
        else:
            op = op_class(self, comm, blocking, cc_id)
            self.collective_operations.append(op)
        context.state.inc_cc_id_counter(comm)
        op.enter(context, comm, args)
        return op

    def finish_collective_operation(self, op):
        self.collective_operations.remove(op)

    def create_new_communicator(self, comm, ranks=None, group=None):
        assert ranks or group
        if ranks:
            pids = [comm.group.rank_to_pid(r) for r in ranks]
            group = Group(pids)
        self.comm_id_counter += 1
        new_comm_id = self.comm_id_counter
        new_comm = Communicator(new_comm_id, group)
        for pid in group.pids():
            self.states[pid].add_comm(new_comm)
        return new_comm

    def clone_communicator(self, comm):
        self.comm_id_counter += 1
        new_comm_id = self.comm_id_counter
        new_comm = Communicator(new_comm_id, comm.group)
        for pid in comm.group.pids():
            self.states[pid].add_comm(new_comm)
        return new_comm

    def sanity_check(self):
        if self.collective_operations is not None:
            for op in self.collective_operations:
                op.sanity_check()

    def mpi_leak_check(self, generator, node):
        for state in self.states:
            state.mpi_leak_check(generator, node)

    def find_nondeterministic_matches(self):
        results = []
        for state in self.states:
            results.extend(state.find_nondeterministic_matches())
        return results

    def get_actions(self, worker):
        actions = [ActionMatching(matching)
                   for matching in self.find_nondeterministic_matches()]
        for state in self.states:
            if state.status == State.StatusWaitAny:
                self.expand_waitany(worker, state, actions)
            elif state.status == State.StatusProbe:
                self.expand_probe(worker, state, actions)
            elif state.status == State.StatusWaitSome:
                self.expand_waitsome(worker, state, actions)
            elif state.status == State.StatusTest:
                self.expand_testall(worker, state, actions)
        return actions

    def expand_waitsome(self, worker, state, actions):
        indices = state.get_indices_of_tested_and_finished_requests()
        if not indices:
            return
        logging.debug("Expanding waitsome %s", state)
        for indices in power_set(indices):
            if not indices:
                continue  # skip empty set
            actions.append(ActionWaitSome(state.pid, indices))

    def expand_testall(self, worker, state, actions):
        logging.debug("Expanding testall %s", state)
        actions.append(ActionFlag0(state.pid))
        if state.are_tested_requests_finished():
            actions.append(ActionTestAll(state.pid))

    def expand_waitany(self, worker, state, actions):
        logging.debug("Expanding waitany %s", state)
        indices = state.get_indices_of_tested_and_finished_requests()
        if not indices:
            return
        for i in indices:
            actions.append(ActionWaitAny(state.pid, i))

    def expand_probe(self, worker, state, actions):
        logging.debug("Expanding probe %s", state)
        comm_id, source, tag, status_ptr = state.probe_data
        if state.get_probe_promise(comm_id, source, tag) is not None:
            return

        if state.flag_ptr:
            actions.append(ActionFlag0(state.pid))
            if source != consts.MPI_ANY_SOURCE:
                probed = state.probe_deterministic(comm_id, source, tag)
                if probed:
                    pid, request = probed
                    rank = request.comm.group.pid_to_rank(pid)
                    actions.append(ActionProbePromise(
                        state.pid, comm_id, source, tag, rank))
        if source != consts.MPI_ANY_SOURCE:
            return
        for pid, request in state.probe_nondeterministic(comm_id, tag):
            rank = request.comm.group.pid_to_rank(pid)
            actions.append(ActionProbePromise(
                state.pid, comm_id, source, tag, rank))
