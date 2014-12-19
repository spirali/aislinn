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
import errormsg

import consts
import copy
import comm
import types
import ops
from keyval import Keyval
import logging

class State:

    StatusReady = 0
    StatusFinished = 1
    StatusWaitAll = 2
    StatusWaitAny = 3
    StatusTest = 4
    StatusProbe = 5

    # Used only for final state, list of non-freed-memory
    allocations = None

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
        self.requests = [] # <-- Copy on write!
        self.persistent_requests = [] # <-- Copy on write!
        self.active_request_ids = None # <-- Copy on write!
        self.active_request_pointer = None
        self.active_request_status_ptr = None
        self.flag_ptr = None
        self.index_ptr = None # Used for Waitany
        self.user_defined_types = [] # <-- Copy on write!
        self.user_defined_ops = [] # <-- Copy on write!
        self.keyvals = [] # <-- Copy on write!
        self.attrs = {} # <-- Copy on write!
        self.cc_id_counters = None
        self.probe_data = None
        self.finalized = False
        self.immediate_wait = False

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
        #state.requests = copy.copy(self.requests)
        state.active_request_ids = copy.copy(self.active_request_ids)
        state.cc_id_counters = copy.copy(self.cc_id_counters)
        return state

    def add_keyval(self, keyval):
        assert keyval.keyval_id is None
        keyval_id = 8000 + len(self.keyvals)
        self.keyvals = copy.copy(self.keyvals)
        self.keyvals.append(keyval)
        keyval.keyval_id = keyval_id

    def remove_keyval(self, keyval):
        self.keyvals = copy.copy(self.keyvals)
        self.keyvals[self.keyvals.index(keyval)] = None

    def get_keyval(self, keyval_id):
        if keyval_id == consts.MPI_TAG_UB:
            keyval = Keyval(None, None, None)
            keyval.keyval_id = keyval_id
            return keyval

        for keyval in self.keyvals:
            if keyval and keyval.keyval_id == keyval_id:
                return keyval

    def set_attr(self, generator, context, comm, keyval, value):
        key = (comm.comm_id, keyval)
        if key in self.attrs:
            self.delete_attr(generator, context, comm, keyval)
        self.attrs = copy.copy(self.attrs)
        self.attrs[key] = value

    def delete_attr(self, generator, context, comm, keyval):
        self.attrs = copy.copy(self.attrs)
        key = (comm.comm_id, keyval)
        value = self.attrs[key]
        del self.attrs[key]
        if keyval.delete_fn != consts.MPI_NULL_DELETE_FN:
            generator.run_function(
                self, context,
                keyval.delete_fn,
                generator.controller.FUNCTION_2_INT_2_POINTER,
                comm.comm_id, keyval.keyval_id, value, keyval.extra_ptr)

    def get_attr(self, comm, keyval):
        return self.attrs.get((comm.comm_id, keyval))

    def get_comm_attrs(self, comm):
        for (comm_id, keyval), value in self.attrs.items():
            if comm_id == comm.comm_id:
                yield keyval, value

    def copy_comm_attrs(self, generator, context, comm, new_comm):
        for keyval, value in self.get_comm_attrs(comm):
            if keyval.copy_fn == consts.MPI_NULL_COPY_FN:
                continue
            tmp = generator.controller.client_malloc(generator.POINTER_SIZE + \
                                                     generator.INT_SIZE)
            value_out_ptr = tmp
            flag_ptr = tmp + generator.POINTER_SIZE

            generator.run_function(
                self, context,
                keyval.copy_fn,
                generator.controller.FUNCTION_2_INT_4_POINTER,
                comm.comm_id, keyval.keyval_id, keyval.extra_ptr,
                value, value_out_ptr, flag_ptr)

            if generator.controller.read_int(flag_ptr):
                self.set_attr(generator, context, new_comm, keyval,
                              generator.controller.read_pointer(value_out_ptr))
            generator.controller.client_free(tmp)

    def add_datatype(self, datatype):
        datatype.type_id = \
            consts.USER_DEFINED_TYPES + len(self.user_defined_types)
        self.user_defined_types = copy.copy(self.user_defined_types)
        self.user_defined_types.append(datatype)

    def remove_datatype(self, datatype):
        self.user_defined_types = copy.copy(self.user_defined_types)
        i = self.user_defined_types.index(datatype)
        self.user_defined_types[i] = None

    def add_op(self, op):
        op.op_id = consts.USER_DEFINED_OPS + len(self.user_defined_ops)
        self.user_defined_ops = copy.copy(self.user_defined_ops)
        self.user_defined_ops.append(op)

    def remove_op(self, op):
        i = self.user_defined_ops.index(op)
        self.user_defined_ops = copy.copy(self.user_defined_ops)
        self.user_defined_ops[i] = None

    def add_comm(self, comm):
        if self.cc_id_counters is None:
            self.cc_id_counters = [0] * (2 + len(self.comms))
        self.cc_id_counters.append(0)
        self.comms = copy.copy(self.comms)
        self.comms.append(comm)

    def remove_comm(self, generator, context, comm):
        for keyval, value in self.get_comm_attrs(comm):
            self.delete_attr(generator, context, comm, keyval)

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

    def get_op(self, op_id):
        op = ops.buildin_operations.get(op_id)
        if op is not None:
            return op
        if op_id >= consts.USER_DEFINED_OPS and \
           op_id < consts.USER_DEFINED_OPS + len(self.user_defined_ops):
               return self.user_defined_ops[op_id
                                              - consts.USER_DEFINED_OPS]
        return None # build-in

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
        else:
            for a in self.allocations:
                a.compute_hash(hashthread)
        hashthread.update(str(self.pid))
        hashthread.update(str(self.status))
        hashthread.update(str(self.cc_id_counters))

        for c in self.comms:
            c.compute_hash(hashthread)

        if self.active_request_ids is not None:
            hashthread.update(str(self.active_request_ids))

        if self.active_request_pointer is not None:
            hashthread.update(str(self.active_request_pointer))

        if self.active_request_status_ptr is not None:
            hashthread.update(str(self.active_request_status_ptr))

        if self.flag_ptr is not None:
            hashthread.update(str(self.flag_ptr))

        if self.index_ptr is not None:
            hashthread.update(str(self.index_ptr))

        # Normalize messages
        self.messages.sort(message_cmp)

        for message in self.messages:
            message.compute_hash(hashthread)

        for request in self.requests:
            request.compute_hash(hashthread)

        for request in self.persistent_requests:
            request.compute_hash(hashthread)

        for op in self.user_defined_ops:
            if op is not None:
                op.compute_hash(hashthread)

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

    def add_request(self, request):
        self.requests = copy.copy(self.requests)
        self.requests.append(request)

    def add_send_request(self, comm_id, target,
                         tag, data_ptr, datatype, count, send_type):
        request_id = self._new_request_id()
        request = SendRequest(request_id, send_type,
                              comm_id, target, tag, data_ptr, datatype, count)
        self.add_request(request)
        logging.debug("New send request pid=%s request_id=%s",
                      self.pid, request_id)
        return request

    def get_request(self, request_id):
        for request in self.requests:
            if request.id == request_id:
                return request
        return None

    def get_request_index(self, request_id):
        if request_id == consts.MPI_REQUEST_NULL:
            return -1
        for i, request in enumerate(self.requests):
            if request.id == request_id:
                return i
        return None

    def get_persistent_request(self, request_id):
        for request in self.persistent_requests:
            if request.id == request_id:
                return request
        return None

    def add_recv_request(self, comm_id, source, tag, data_ptr, datatype, count):
        request_id = self._new_request_id()
        request = ReceiveRequest(
                request_id, comm_id, source, tag, data_ptr, datatype, count)
        self.add_request(request)
        logging.debug("New recv request pid=%s request_id=%s",
                      self.pid, request_id)
        return request

    def make_request_persistent(self, request_id):
        request = self.get_request(request_id)
        self.requests = copy.copy(self.requests)
        self.requests.remove(request)
        self.persistent_requests = copy.copy(self.persistent_requests)
        self.persistent_requests.append(request)

    def remove_persistent_request(self, request):
        self.persistent_requests = copy.copy(self.persistent_requests)
        self.persistent_requests.remove(request)

    def start_persistent_request(self, generator, state, request):
        assert self.get_request(request.id) is None
        request = copy.copy(request)
        request.stacktrace = generator.controller.get_stacktrace()
        if request.is_send():
            self.add_request(request)
            if request.target == consts.MPI_PROC_NULL:
                state.set_request_as_completed(request)
            else:
                request.create_message(generator, state)
                if request.send_type == SendRequest.Buffered:
                    state.set_request_as_completed(request)

            sz = request.count * request.datatype.size
            r = generator.controller.is_writable(request.data_ptr, sz)
            if r != "Ok":
                e = errormsg.CallError()
                e.name = "invalid-send-buffer"
                e.short_description = "Invalid send buffer"
                e.description = "Invalid receive buffer. " \
                                "Address 0x{0:x} is not accessible.".format(int(r))
                e.throw()
            generator.controller.lock_memory(request.data_ptr, sz)

        elif request.is_receive():
            sz = request.count * request.datatype.size
            r = generator.controller.is_writable(request.data_ptr, sz)
            if r != "Ok":
                e = errormsg.CallError()
                e.name = "invalid-recv-buffer"
                e.short_description = "Invalid receive buffer"
                e.description = "Invalid receive buffer. " \
                                "Address 0x{0:x} is not accessible.".format(int(r))
                e.throw()
            generator.controller.lock_memory(
                    request.data_ptr,
                    request.count * request.datatype.size)
            self.add_request(request)
        else:
            Exception("Invalid request")

    def add_collective_request(self, comm_id, cc_id):
        request_id = self._new_request_id()
        request = CollectiveRequest(request_id, comm_id, cc_id)
        self.add_request(request)
        return request_id

    def _finish_request(self, generator, request,
                        index_pointer, index_status):
        assert request.is_completed()
        message = request.message
        request = request.original_request
        if not self.immediate_wait and (request.is_send() or request.is_receive()):
            generator.controller.unlock_memory(request.data_ptr,
                                               request.datatype.size * request.count)

        if self.active_request_pointer is not None and \
                self.get_persistent_request(request.id) is None:
            generator.controller.write_int(
                    self.active_request_pointer + \
                    generator.REQUEST_SIZE * index_pointer,
                    consts.MPI_REQUEST_NULL)
        if self.active_request_status_ptr is not None and request.is_receive():
            status_ptr = self.active_request_status_ptr + \
                         generator.STATUS_SIZE * index_status
            if request.source == consts.MPI_PROC_NULL:
                generator.write_status(status_ptr,
                                  consts.MPI_PROC_NULL,
                                  consts.MPI_ANY_TAG,
                                  0)
            else:
                generator.write_status(status_ptr,
                          message.source,
                          message.tag,
                          message.size)

    def finish_active_requests(self, generator):
        logging.debug("Removing active requests")
        self.requests = copy.copy(self.requests)
        for index, request_id in enumerate(self.active_request_ids):
            request = self.get_request(request_id)
            self._finish_request(generator, request, index, index)
            self.requests.remove(request)
        self.active_request_ids = None

    def finish_active_request(self, generator, request):
        index = self.active_request_ids.index(request.id)
        self._finish_request(generator, request, index, 0)
        self.requests = copy.copy(self.requests)
        self.requests.remove(request)
        self.active_request_ids = copy.copy(self.active_request_ids)
        del self.active_request_ids[index]

    def reset_state(self):
        self.status = None
        self.active_request_ids = None
        self.active_request_pointer = None
        self.active_request_status_ptr = None
        self.flag_ptr = None
        self.index_ptr = None
        self.probe_data = None
        self.immediate_wait = False

    def set_ready(self):
        self.reset_state()
        self.status = self.StatusReady

    def set_probe(self, comm, source, tag, flag_ptr, status_ptr):
        self.reset_state()
        self.status = self.StatusProbe
        self.probe_data = (comm.comm_id, source, tag, flag_ptr, status_ptr)

    def set_wait(self,
                 request_ids,
                 request_ptr=None,
                 status_ptr=None,
                 wait_any=False,
                 index_ptr=None,
                 immediate=False):
        self.reset_state()
        # This wait was called immediately after creating request,
        # hence buffers are not locked
        self.immediate_wait = immediate
        if wait_any:
            self.status = self.StatusWaitAny
            self.index_ptr = index_ptr
        else:
            self.status = self.StatusWaitAll
        self.active_request_ids = request_ids
        self.active_request_pointer = request_ptr
        self.active_request_status_ptr = status_ptr

    def set_finished(self):
        self.reset_state()
        self.status = self.StatusFinished

    def set_test(self, request_ids, flag_ptr, request_ptr, status_ptr):
        self.status = self.StatusTest
        self.active_request_ids = request_ids
        self.flag_ptr = flag_ptr
        self.active_request_pointer = request_ptr
        self.active_request_status_ptr = status_ptr

    def set_request_as_completed(self, request, message=None):
        assert not request.is_completed()
        self.requests = copy.copy(self.requests)
        i = self.requests.index(request)
        self.requests[i] = CompletedRequest(request.id, request, message)

    def set_request_as_synchronous(self, request):
        assert request.is_standard_send()
        self.requests = copy.copy(self.requests)
        i = self.requests.index(request)
        request = copy.copy(request)
        request.send_type = SendRequest.Synchronous
        self.requests[i] = request

    def is_matching_covering_active_requests(self, matching):
        for request_id in self.active_request_ids:
            if request_id == consts.MPI_REQUEST_NULL:
                # Ignore MPI_REQUEST_NULL, it get here through MPI_Waitany
                continue
            request = self.get_request(request_id)
            if request.is_completed():
                continue
            for r, message in matching:
                if r is request:
                    break
            else:
                return False
        return True

    def active_requests_covered_by_matching(self, matching):
        result = []
        for i, request_id in enumerate(self.active_request_ids):
            if request_id == consts.MPI_REQUEST_NULL:
                # Ignore MPI_REQUEST_NULL, it get here through MPI_Waitany
                continue
            request = self.get_request(request_id)
            if request.is_completed():
                result.append((i, request))
                continue
            for r, message in matching:
                if r is request:
                    result.append((i, request))
        return result

    def check_requests(self, upto_active=False):
        if upto_active:
            max_index = max(self.get_request_index(id)
                            for id in self.active_request_ids)
            requests = self.requests[:max_index+1]
        else:
            requests = self.requests
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
        max_index = max(self.get_request_index(id)
                        for id in self.active_request_ids)
        for i in xrange(max_index + 1):
            if not self.requests[i].is_deterministic():
                return False
        return True

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
        max_index = max(self.get_request_index(id)
                        for id in self.active_request_ids)
        result = [ ([], []) ]
        for i in xrange(max_index + 1):
            request = self.requests[i]
            if request.is_send() and request.is_standard_send():
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

    def get_locked_memory_stacktrace(self, addr):
        for request in self.requests:
            if request.is_data_addr(addr):
                return request.stacktrace

    def _new_request_id(self):
        i = 10
        while True:
            for request in self.requests:
                if i == request.id:
                    break
            else:
                for request in self.persistent_requests:
                    if i == request.id:
                        break
                else:
                    return i
            i += 1

    def __repr__(self):
        return "<state {0:x} pid={1}>".format(id(self), self.pid)

# Used for message normalization
# Matching cannot depenend on order messages according to
# comm_id and source process
def message_cmp(m1, m2):
    r = cmp(m1.comm_id, m1.comm_id)
    if r == 0:
        return cmp(m1.source, m2.source)
    return r
