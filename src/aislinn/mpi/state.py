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


from message import Message
from request import SendRequest, ReceiveRequest, CompletedRequest
import consts
import copy

class State:

    StatusInited = 0
    StatusFinished = 1
    StatusWait = 2
    StatusTest = 3

    def __init__(self, rank, vg_state):
        assert vg_state is not None
        self.rank = rank
        self.vg_state = vg_state
        self.status = State.StatusInited
        self.messages = []
        self.requests = [None]
        self.active_request_ids = None
        self.flag_ptr = None

    def copy(self):
        if self.status == State.StatusFinished:
            assert self.vg_state is None
            for message in self.messages:
                message.vg_buffer.inc_ref()
            # Process cannot evolve anymore so we can see it as immutable
            return self
        if self.vg_state:
            self.vg_state.inc_ref()
        state = State(self.rank, self.vg_state)
        state.status = self.status
        state.messages = copy.copy(self.messages)
        for message in state.messages:
            message.vg_buffer.inc_ref()
        state.requests = copy.copy(self.requests)
        state.active_request_ids = copy.copy(self.active_request_ids)
        state.flag_ptr = self.flag_ptr
        return state

    def dispose(self):
        if self.vg_state is not None:
            self.vg_state.dec_ref()
        for message in self.messages:
            message.vg_buffer.dec_ref()

    def is_hashable(self):
        # If we are finished, we do not care about exact state
        return self.status == State.StatusFinished or \
               (self.vg_state is not None and self.vg_state.hash is not None)

    def compute_hash(self, hashthread):
        assert self.is_hashable()
        if self.status != State.StatusFinished:
            # If we are finished, we do not care about exact state
            hashthread.update(self.vg_state.hash)
        hashthread.update(str(self.rank))
        hashthread.update(str(self.status))
        if self.active_request_ids is not None:
            hashthread.update(str(self.active_request_ids))
        if self.flag_ptr is not None:
            hashthread.update(str(self.flag_ptr))
        for message in self.messages:
            message.compute_hash(hashthread)
        for request in self.requests:
            if request is not None:
                request.compute_hash(hashthread)

    def add_message(self, source, target, tag, vg_buffer, size, hash):
        message = Message(source, target, tag, vg_buffer, size, hash)
        self.messages.append(message)
        return message

    def remove_message(self, message):
        message.vg_buffer.dec_ref()
        self.messages.remove(message)

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

    def add_recv_request(self, source, tag, data_ptr, size):
        request_id = self._new_request_index()
        request = ReceiveRequest(source, tag, data_ptr, size)
        self.requests[request_id] = request
        return request_id

    def find_request(self, request_id):
        return self.requests[request_id]

    def remove_active_requests(self):
        for request_id in self.active_request_ids:
            assert self.requests[request_id].is_completed()
            self.requests[request_id] = None
        self.active_request_ids = None

    def reset_state(self):
        self.status = None
        self.active_request_ids = None
        self.flag_ptr = None

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

    def set_test(self, request_ids, flag_ptr):
        self.status = self.StatusTest
        self.active_request_ids = request_ids
        self.flag_ptr = flag_ptr

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

    def check_requests(self, gstate, upto_active=False):
        if upto_active:
            max_id = max(self.active_request_ids)
            requests = [ request for request in self.requests[:max_id+1]
                         if request is not None ]
        else:
            requests = [ request for request in self.requests
                         if request is not None ]
        non_recv_requests = []

        for r in requests:
            if r.is_send():
                s = gstate.get_state(r.message.target)
                if r.message not in s.messages:
                    non_recv_requests.append((r, None))

        result = []
        recvs = [ r for r in requests if r.is_receive() ]
        if recvs:
            matching = self.collect_messages(gstate, recvs)
            if matching:
                for matched in self.collect_messages(gstate, recvs):
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
            if request.is_receive() and request.source == consts.MPI_ANY_SOURCE:
                return False
        return True

    def is_request_id_valid(self, request_id):
        if request_id < 0 or request_id >= len(self.requests):
            return False
        return self.requests[request_id] is not None

    def collect_messages(self, gstate, requests):
        matched = [] # [(request, message)]
        result = [] # [[(request, message)]]
        def already_matched(message):
            for r, m in matched:
                if m == message:
                    return True
            return False
        def collect_messages_helper(index):
            if index == len(requests):
                result.append(matched[:])
                return
            request = requests[index]
            flags = [ False ] * gstate.states_count
            found = False

            for message in self.messages:
                if (request.source == consts.MPI_ANY_SOURCE \
                        or request.source == message.source) and \
                        (request.tag == consts.MPI_ANY_TAG or request.tag == message.tag) \
                        and not flags[message.source]:
                    if already_matched(message):
                         continue # Message already taken from other request
                    flags[message.source] = True
                    found = True
                    matched.append((request, message))
                    collect_messages_helper(index + 1)
                    matched.pop()

            if not found:
                collect_messages_helper(index + 1)
        collect_messages_helper(0)
        return result

    def fork_standard_sends(self, gstate):
        max_id = max(self.active_request_ids)
        result = [ ([], []) ]
        for i in xrange(max_id + 1):
            request = self.requests[i]
            if request and request.is_send() and request.is_standard_send():
                s = gstate.get_state(request.message.target)
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
