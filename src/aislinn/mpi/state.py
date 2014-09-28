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


from request import \
    SendRequest, \
    ReceiveRequest, \
    CompletedRequest, \
    CollectiveRequest
import consts
import copy
import comm
import types

class State:

    StatusReady = 0
    StatusFinished = 1
    StatusWait = 2
    StatusTest = 3
    StatusProbe = 4

    def __init__(self, gstate, pid, vg_state):
        assert vg_state is not None
        self.gstate = gstate
        self.pid = pid
        self.vg_state = vg_state
        self.status = State.StatusReady
        self.messages = []
        self.probed_messages = None # [ (comm_id, source, tag, message) ] or None
        self.comms = [] # <-- Copy on write!
        self.groups = {} # <-- Copy on write!
        self.requests = [None]
        self.active_request_ids = None
        self.flag_ptr = None
        self.user_defined_types = [] # <-- Copy on write!
        self.cc_id_counters = None
        self.probe_data = None
        self.finalized = False

        # cc_id_counters - when first touched, is should be
        # a list of length len(self.cc_id_coutners) = 2 + len(self.comms)
        # First two indexes are reserved for MPI_COMM_WORLD and MPI_COMM_SELF

    def copy(self, gstate):
        if self.status == State.StatusFinished:
            assert self.vg_state is None
            for message in self.messages:
                message.vg_buffer.inc_ref()
            # Process cannot evolve anymore so we can see it as immutable
            return self
        if self.vg_state:
            self.vg_state.inc_ref()
        state = copy.copy(self)
        state.gstate = gstate
        state.messages = copy.copy(self.messages)
        for message in state.messages:
            message.vg_buffer.inc_ref()
        if self.probed_messages is not None:
            state.probed_messages = copy.copy(self.probed_messages)
        state.requests = copy.copy(self.requests)
        state.active_request_ids = copy.copy(self.active_request_ids)
        state.cc_id_counters = copy.copy(self.cc_id_counters)
        return state

    def add_datatype(self, datatype):
        datatype.type_id = \
            consts.USER_DEFINED_TYPES + len(self.user_defined_types)
        self.user_defined_types = copy.copy(self.user_defined_types)
        self.user_defined_types.append(datatype)

    def remove_datatype(self, datatype):
        self.user_defined_types = copy.copy(self.user_defined_types)
        i = self.user_defined_types.index(datatype)
        self.user_defined_types[i] = None

    def add_comm(self, comm):
        if self.cc_id_counters is None:
            self.cc_id_counters = [0] * (2 + len(self.comms))
        self.cc_id_counters.append(0)
        self.comms = copy.copy(self.comms)
        self.comms.append(comm)

    def remove_comm(self, comm):
        self.comms = copy.copy(self.comms)
        i = self.comms.index(comm)
        del self.cc_id_counters[i + 2]
        del self.comms[i]

    def add_group(self, group):
        self.groups = copy.copy(self.groups)
        i = consts.MPI_GROUP_NULL + 1
        while True:
            if i not in self.groups:
                break
            i += 1
        self.groups[i] = group
        return i

    def remove_group(self, group):
        self.groups = copy.copy(self.groups)
        for i, g in self.groups.items():
            if g is group:
                del self.groups[i]
                return
        raise Exception("Group not found")



    def get_group(self, group_id):
        return self.groups.get(group_id)

    def dispose(self):
        if self.vg_state is not None:
            self.vg_state.dec_ref()
        for message in self.messages:
            message.vg_buffer.dec_ref()

    def get_datatype(self, type_id):
        if type_id >= consts.USER_DEFINED_TYPES and \
           type_id < consts.USER_DEFINED_TYPES + len(self.user_defined_types):
               return self.user_defined_types[type_id
                                              - consts.USER_DEFINED_TYPES]
        return types.buildin_types.get(type_id)

    def commit_datatype(self, datatype):
        """ datatype has to be valid type for this state """
        if datatype.type_id >= consts.USER_DEFINED_TYPES:
            i = datatype.type_id - consts.USER_DEFINED_TYPES
            assert self.user_defined_types[i] == datatype
            self.user_defined_types = copy.copy(self.user_defined_types)
            self.user_defined_types[i] == copy.copy(datatype)
            self.user_defined_types[i].commited = True
        # Build in types are already commited

    def _cc_id_counter_index(self, comm):
        if comm.comm_id == consts.MPI_COMM_WORLD:
            return 0
        if comm.comm_id == consts.MPI_COMM_SELF:
            return 1
        for i, c in enumerate(self.comms):
            if c.comm_id == comm.comm_id:
                return 2 + i

    def get_cc_id_counter(self, comm):
        if self.cc_id_counters is None:
            self.cc_id_counters = [0] * (2 + len(self.comms))
        return self.cc_id_counters[self._cc_id_counter_index(comm)]

    def inc_cc_id_counter(self, comm):
        if self.cc_id_counters is None:
            self.cc_id_counters = [0] * (2 + len(self.comms))
        self.cc_id_counters[self._cc_id_counter_index(comm)] += 1

    def is_hashable(self):
        # If we are finished, we do not care about exact state
        return self.status == State.StatusFinished or \
               (self.vg_state is not None and self.vg_state.hash is not None)

    def compute_hash(self, hashthread):
        assert self.is_hashable()
        if self.status != State.StatusFinished:
            # If we are finished, we do not care about exact state
            hashthread.update(self.vg_state.hash)
        hashthread.update(str(self.pid))
        hashthread.update(str(self.status))
        hashthread.update(str(self.cc_id_counters))

        for c in self.comms:
            c.compute_hash(hashthread)

        if self.active_request_ids is not None:
            hashthread.update(str(self.active_request_ids))
        if self.flag_ptr is not None:
            hashthread.update(str(self.flag_ptr))

        # Normalize messages
        self.messages.sort(message_cmp)

        for message in self.messages:
            message.compute_hash(hashthread)
        for request in self.requests:
            if request is not None:
                request.compute_hash(hashthread)

    def add_message(self, message):
        self.messages.append(message)
        return message

    def remove_message(self, message):
        if self.probed_messages:
            for i, v in enumerate(self.probed_messages[:]):
                cid, s, t, m = v
                if m == message:
                    self.probed_messages.remove(v)
        self.messages.remove(message)
        message.vg_buffer.dec_ref()

    def add_standard_send_request(self, message):
        request_id = self._new_request_index()
        request = SendRequest(message, SendRequest.Standard)
        self.requests[request_id] = request
        return request_id

    def add_synchronous_send_request(self, message):
        request_id = self._new_request_index()
        request = SendRequest(message, SendRequest.Synchronous)
        self.requests[request_id] = request
        return request_id

    def add_completed_request(self):
        request_id = self._new_request_index()
        request = CompletedRequest(None)
        self.requests[request_id] = request
        return request_id

    def add_recv_request(self, comm_id, source, tag, data_ptr, datatype, count):
        request_id = self._new_request_index()
        request = ReceiveRequest(
                comm_id, source, tag, data_ptr, datatype, count)
        self.requests[request_id] = request
        return request_id

    def add_collective_request(self, comm_id, cc_id):
        request_id = self._new_request_index()
        request = CollectiveRequest(comm_id, cc_id)
        self.requests[request_id] = request
        return request_id

    def find_request(self, request_id):
        return self.requests[request_id]

    def remove_active_requests(self):
        for request_id in self.active_request_ids:
            assert self.requests[request_id].is_completed()
            self.requests[request_id] = None
        self.active_request_ids = None

    def reinit_active_requests(self):
        if self.active_request_ids:
            for request_id in self.active_request_ids:
                self.requests[request_id].status_ptr = None

    def reset_state(self):
        self.status = None
        self.active_request_ids = None
        self.flag_ptr = None
        self.probe_data = None

    def set_ready(self):
        self.reset_state()
        self.status = self.StatusReady

    def set_probe(self, comm, source, tag, flag_ptr, status_ptr):
        self.reset_state()
        self.status = self.StatusProbe
        self.probe_data = (comm.comm_id, source, tag, flag_ptr, status_ptr)

    def set_wait(self, request_ids, status_ptrs=None):
        self.reset_state()
        self.status = self.StatusWait
        self.active_request_ids = request_ids
        if status_ptrs is not None:
            for i, ptr in zip(request_ids, status_ptrs):
                request = self.requests[i]
                assert request.status_ptr is None
                request.status_ptr = ptr

    def set_finished(self):
        self.reset_state()
        self.status = self.StatusFinished

    def set_test(self, request_ids, flag_ptr, status_ptrs):
        self.status = self.StatusTest
        self.active_request_ids = request_ids
        self.flag_ptr = flag_ptr

        if status_ptrs is not None:
            for i, ptr in zip(request_ids, status_ptrs):
                request = self.requests[i]
                assert request.status_ptr is None
                request.status_ptr = ptr

    def set_request_as_completed(self, request):
        assert not request.is_completed()
        i = self.requests.index(request)
        self.requests[i] = CompletedRequest(request)

    def set_request_as_synchronous(self, request):
        assert request.is_standard_send()
        i = self.requests.index(request)
        self.requests[i] = SendRequest(request.message, SendRequest.Synchronous)

    def is_matching_covers_active_requests(self, matching):
        for request_id in self.active_request_ids:
            request = self.requests[request_id]
            if request.is_completed():
                continue
            for r, message in matching:
                if r is request:
                    break
            else:
                return False
        return True

    def check_requests(self, upto_active=False):
        if upto_active:
            max_id = max(self.active_request_ids)
            requests = [ request for request in self.requests[:max_id+1]
                         if request is not None ]
        else:
            requests = [ request for request in self.requests
                         if request is not None ]
        non_recv_requests = []
        gstate = self.gstate

        for r in requests:
            if r.is_send():
                s = self.gstate.get_state(r.message.target)
                if r.message not in s.messages:
                    non_recv_requests.append((r, None))
            if r.is_collective():
                if gstate.get_operation_by_cc_id(r.comm_id, r.cc_id) \
                        .can_be_completed(self):
                    non_recv_requests.append((r, None))
            if r.is_receive() and r.source == consts.MPI_PROC_NULL:
                non_recv_requests.append((r, None))

        result = []
        recvs = [ r for r in requests
                  if r.is_receive() and r.source != consts.MPI_PROC_NULL ]
        if recvs:
            matching = self.collect_messages(recvs)
            if matching:
                for matched in matching:
                    result.append(non_recv_requests + matched)
            else:
                result.append(non_recv_requests)
        else:
            result.append(non_recv_requests)
        return result

    def are_requests_deterministic(self):
        max_id = max(self.active_request_ids)
        for i in xrange(max_id + 1):
            request = self.requests[i]
            if request is None:
                continue
            if not request.is_deterministic():
                return False
        return True

    def is_request_id_valid(self, request_id):
        if request_id < 0 or request_id >= len(self.requests):
            return False
        return self.requests[request_id] is not None

    def probe_messages(self, comm_id, source, tag):
        messages = []

        if self.probed_messages:
            for cid, s, t, m in self.probed_messages:
                if comm_id == cid and s == source and t == tag:
                    messages.append(m)
                    return messages, True

        ranks = []

        for message in self.messages:
            if (comm_id == message.comm_id) and \
               (source == consts.MPI_ANY_SOURCE or
                    source == message.source) and \
               (tag == consts.MPI_ANY_TAG or
                    tag == message.tag) and \
               source not in ranks:
                   ranks.append(message.source)
                   messages.append(message)
        return messages, False

    def add_probed_message(self, comm_id, source, tag, message):
        if self.probed_messages is None:
            self.probed_messages = []
        for cid, s, t, m in self.probed_messages:
            if comm_id == cid and s == source and t == tag:
                assert m == message
                return
        self.probed_messages.append((comm_id, source, tag, message))

    def collect_messages(self, requests):
        matched = [] # [(request, message)]
        result = [] # [[(request, message)]]

        if self.probed_messages is not None:
            probed_messages = self.probed_messages[:]
        else:
            probed_messages = None

        def already_matched(message):
            for r, m in matched:
                if m == message:
                    return True
            return False

        def collect_messages_helper(index):
            def match(reqeust, message):
                flags[message.source] = True
                matched.append((request, message))
                collect_messages_helper(index + 1)
                matched.pop()


            if index == len(requests):
                result.append(matched[:])
                return
            request = requests[index]
            flags = [ False ] * self.gstate.process_count
            found = False

            if probed_messages:
                for v in probed_messages:
                    cid, s, t, m = v
                    if (request.comm_id == cid and
                            request.source == s and
                            request.tag == t):
                        if already_matched(m):
                            continue
                        found = True
                        probed_messages.remove(v)
                        match(request, m)
                        probed_messages.append(v)
                        break

            if not found:
                for message in self.messages:
                    if (request.comm_id == message.comm_id) and \
                       (request.source == consts.MPI_ANY_SOURCE or
                            request.source == message.source) and \
                       (request.tag == consts.MPI_ANY_TAG or
                            request.tag == message.tag) and \
                       not flags[message.source]:
                        if already_matched(message):
                             continue # Message already taken from other request
                        found = True
                        match(request, message)

            if not found:
                collect_messages_helper(index + 1)
        collect_messages_helper(0)
        return result

    def fork_standard_sends(self):
        max_id = max(self.active_request_ids)
        result = [ ([], []) ]
        for i in xrange(max_id + 1):
            request = self.requests[i]
            if request and request.is_send() and request.is_standard_send():
                s = self.gstate.get_state(request.message.target)
                if request.message not in s.messages:
                    continue # Message is received so this send is not a problem
                             # even in synchronous variant
                new_result = []
                for buffered, synchronous  in result:
                    b = buffered[:]
                    buffered.append(request)
                    s = synchronous[:]
                    synchronous.append(request)
                    new_result.append((b, synchronous))
                    new_result.append((buffered, s))
                result = new_result

        if len(result) == 1: # Nothing changed
            return None
        else:
            return result

    def get_comm(self, comm_id):
        if comm_id == consts.MPI_COMM_WORLD:
            return self.gstate.comm_world
        if comm_id == consts.MPI_COMM_SELF:
            return comm.make_comm_self(self.pid)
        for c in self.comms:
            if c.comm_id == comm_id:
                return c

    def get_rank(self, comm):
        return comm.group.pid_to_rank(self.pid)

    def _new_request_index(self):
        i = len(self.requests) - 1
        if self.requests[i] is not None:
            self.requests.append(None)
            return i + 1
        i -= 1
        while i >= 0:
            if self.requests[i] is not None:
                return i + 1
            i -= 1
        return 0

# Used for message normalization
# Matching cannot depenend on order messages according to
# comm_id and source process
def message_cmp(m1, m2):
    r = cmp(m1.comm_id, m1.comm_id)
    if r == 0:
        return cmp(m1.source, m2.source)
    return r
