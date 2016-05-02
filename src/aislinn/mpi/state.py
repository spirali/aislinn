#
#    Copyright (C) 2014, 2016 Stanislav Bohm
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


from request import \
    Request, \
    CollectiveRequest
from base.utils import Intervals
import errormsg
import request

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
    StatusWaitSome = 4
    StatusTest = 5
    StatusProbe = 6

    # Used only for final state, list of non-freed-memory
    allocations = None

    def __init__(self, gstate, pid, vg_state, loader=None):
        self.gstate = gstate
        if loader is None:
            self.pid = pid
            self.vg_state = vg_state
            self.status = State.StatusReady
            self.comms = []  # <-- Copy on write!
            self.groups = {}  # <-- Copy on write!
            self.active_requests = []  # <-- Copy on write!
            self.finished_requests = []  # <-- Copy on write!
            self.persistent_requests = []  # <-- Copy on write!
            self.tested_request_ids = []
            self.tested_requests_pointer = None
            self.tested_requests_status_ptr = None
            self.flag_ptr = None
            self.index_ptr = None  # Used for Waitany and WaitSome
            self.user_defined_types = []  # <-- Copy on write!
            self.user_defined_ops = []  # <-- Copy on write!
            self.keyvals = []  # <-- Copy on write!
            self.attrs = {}  # <-- Copy on write!
            self.cc_id_counters = None
            self.probe_data = None
            self.probe_promise = None
            self.finalized = False
            self.immediate_wait = False
            self.locked_memory = Intervals()  # <-- Copy on write!
        else:
            self.pid = loader.get()
            self.vg_state = loader.get_object()
            self.status = loader.get()
            comms = loader.get()
            groups = loader.get()
            active_requests = loader.get()
            finished_requests = loader.get()
            persistent_requests = loader.get()
            self.tested_request_ids = loader.get()
            self.tested_requests_pointer = loader.get()
            self.tested_requests_status_ptr = loader.get()
            self.flag_ptr = loader.get()
            self.index_ptr = loader.get()
            user_defined_types = loader.get()
            user_defined_ops = loader.get()
            keyvals = loader.get()
            attrs = loader.get()
            self.cc_id_counters = loader.get()
            self.probe_data = loader.get()
            self.probe_promise = loader.get()
            self.finalized = loader.get()
            self.immediate_wait = loader.get()
            allocations = loader.get()

            self.comms = [comm.load_communicator(loader)
                          for i in xrange(comms)]
            self.groups = [comm.load_group(loader) for i in xrange(groups)]

            self.user_defined_types = []
            for i in xrange(user_defined_types):
                self.user_defined_types.append(
                    types.deserialize_datatype(loader, self))

            self.user_defined_ops = [
                ops.UserDefinedOperation.deserialize_from_list(loader)
                for i in xrange(user_defined_ops)]

            self.keyvals = [Keyval.deserialize_from_list(loader)
                            for i in xrange(keyvals) ]

            self.attrs = {}
            for i in xrange(attrs):
                key = (loader.get(), loader.get())
                self.attrs[key] = loader.get()

            # Requests
            self.active_requests = [request.load_request(loader, self)
                                    for i in xrange(active_requests)]
            self.finished_requests = [request.load_request(loader, self)
                                      for i in xrange(finished_requests)]
            self.persistent_requests = [request.load_request(loader, self)
                                        for i in xrange(persistent_requests)]
            assert allocations is None
            self.locked_memory = Intervals(loader.get())

        # cc_id_counters - when first touched, is should be
        # a list of length len(self.cc_id_coutners) = 2 + len(self.comms)
        # First two indexes are reserved for MPI_COMM_WORLD and MPI_COMM_SELF

    def serialize_to_list(self):
        # We are implementing own serialization to maintain
        # hash invariant (it does not hold for pickle)
        # The problem is mainly vg_state and vg_buffers (in cc and requests)

        assert self.vg_state is not None or self.status == self.StatusFinished

        lst = [self.pid,
               self.vg_state.hash if self.vg_state is not None else None,
               self.status,
               len(self.comms),
               len(self.groups),
               len(self.active_requests),
               len(self.finished_requests),
               len(self.persistent_requests),
               self.tested_request_ids,
               self.tested_requests_pointer,
               self.tested_requests_status_ptr,
               self.flag_ptr,
               self.index_ptr,
               len(self.user_defined_types),
               len(self.user_defined_ops),
               len(self.keyvals),
               len(self.attrs),
               self.cc_id_counters,
               self.probe_data,
               self.probe_promise,
               self.finalized,
               self.immediate_wait,
               len(self.allocations) if self.allocations else None
              ]

        for i in self.comms:
            i.serialize_to_list(lst)
        for i in self.groups:
            i.serialize_to_list(lst)
        for i in self.user_defined_types:
            if i is None:
                lst.append(None)
            else:
                i.serialize_to_list(lst)
        for i in self.user_defined_ops:
            if i is None:
                lst.append(None)
            else:
                i.serialize_to_list(lst)
        for i in self.keyvals:
            if i is None:
                lst.append(None)
            else:
                i.serialize_to_list(lst)
        for key, value in sorted(self.attrs.items()):
            lst.append(key[0]) # comm_id
            lst.append(key[1]) # keyval_id
            lst.append(value)

        # Requests
        for i in self.active_requests:
            i.serialize_to_list(lst)
        for i in self.finished_requests:
            i.serialize_to_list(lst)
        for i in self.persistent_requests:
            i.serialize_to_list(lst)

        if self.allocations:
            for i in self.allocations:
                i.serialize_to_list(lst)

        self.locked_memory.serialize_to_list(lst)
        return lst

    def copy(self, gstate):
        logging.debug("Copying state %s", self)
        if self.vg_state:
            self.vg_state.inc_ref()
        state = copy.copy(self)
        state.gstate = gstate
        for request in state.active_requests:
            request.inc_ref()
        for request in state.finished_requests:
            request.inc_ref()
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

    def set_attr(self, context, comm, keyval, value):
        key = (comm.comm_id, keyval.keyval_id)
        if key in self.attrs:
            self.delete_attr(context, comm, keyval)
        self.attrs = copy.copy(self.attrs)
        self.attrs[key] = value

    def delete_attr(self, context, comm, keyval):
        self.attrs = copy.copy(self.attrs)
        key = (comm.comm_id, keyval.keyval_id)
        value = self.attrs.pop(key)
        if keyval.delete_fn != consts.MPI_NULL_DELETE_FN:
            context.run_function(
                keyval.delete_fn,
                context.controller.FUNCTION_2_INT_2_POINTER,
                comm.comm_id, keyval.keyval_id, value, keyval.extra_ptr)

    def get_attr(self, comm, keyval):
        return self.attrs.get((comm.comm_id, keyval.keyval_id))

    def get_comm_attrs(self, comm):
        for (comm_id, keyval_id), value in self.attrs.items():
            if comm_id == comm.comm_id:
                keyval = self.get_keyval(keyval_id)
                assert keyval
                yield keyval, value

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

    def remove_comm(self, context, comm):
        for keyval, value in self.get_comm_attrs(comm):
            self.delete_attr(context, comm, keyval)

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
        for request in self.active_requests:
            request.dec_ref()
        for request in self.finished_requests:
            request.dec_ref()

    def get_datatype(self, type_id):
        if type_id >= consts.USER_DEFINED_TYPES and \
                type_id < consts.USER_DEFINED_TYPES + \
                len(self.user_defined_types):
            return self.user_defined_types[type_id - consts.USER_DEFINED_TYPES]
        return types.buildin_types.get(type_id)

    def get_op(self, op_id):
        op = ops.buildin_operations.get(op_id)
        if op is not None:
            return op
        if op_id >= consts.USER_DEFINED_OPS and \
                op_id < consts.USER_DEFINED_OPS + len(self.user_defined_ops):
            return self.user_defined_ops[op_id - consts.USER_DEFINED_OPS]
        return None  # build-in

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

    def is_serializable(self):
        # If we are finished, we do not care about exact state
        return self.status == State.StatusFinished or \
            (self.vg_state is not None and self.vg_state.hash is not None)

    def add_request(self, request):
        self.active_requests = copy.copy(self.active_requests)
        self.active_requests.append(request)

    def add_finished_request(self, request):
        self.finished_requests = copy.copy(self.finished_requests)
        self.finished_requests.append(request)

    def add_persistent_request(self, request):
        self.persistent_requests = copy.copy(self.persistent_requests)
        self.persistent_requests.append(request)

    def lock_memory(self, context, regions):
        self.locked_memory = self.locked_memory.copy()
        for start, size in regions:
            for begin, end in self.locked_memory.add(start, start + size):
                context.controller.lock_memory(begin, end - begin)

    def unlock_memory(self, context, regions):
        self.locked_memory = self.locked_memory.copy()
        for start, size in regions:
            for begin, end in self.locked_memory.remove(start, start + size):
                context.controller.unlock_memory(begin, end - begin)

    def activate_request(self, context, request, immediate):
        if request.is_send():
            if request.target == consts.MPI_PROC_NULL:
                self.add_finished_request(request)
                return
            r = request.datatype.check(
                context.controller, request.data_ptr, request.count, read=True)
            if r is not None:
                e = errormsg.InvalidSendBuffer(context, address=int(r))
                context.add_error_and_throw(e)
            request.create_message(context)
            if request.send_type != Request.TYPE_SEND_RENDEZVOUS:
                request.inc_ref()
                self.add_finished_request(request)
        elif request.is_receive():
            self.probe_promise = None
            if request.source == consts.MPI_PROC_NULL:
                self.add_finished_request(request)
                return
            r = request.datatype.check(context.controller,
                                       request.data_ptr,
                                       request.count,
                                       write=True)
            if r is not None:
                e = errormsg.InvalidReceiveBuffer(context, address=int(r))
                context.add_error_and_throw(e)

        self.add_request(request)

        if context.event.new_request is None:
            context.event.new_request = request.id
        elif isinstance(context.event.new_request, list):
            context.event.new_request.append(request.id)
        else:
            context.event.new_request = [context.event.new_request, request.id]

        if not immediate:
            request.stacktrace = context.event.stacktrace
            regions = []
            request.datatype.memory_regions(
                request.data_ptr, request.count, regions)
            self.lock_memory(context, regions)

    def get_finished_request(self, request_id):
        for request in self.finished_requests:
            if request.id == request_id:
                return request

    def get_request(self, request_id, raise_error=False):
        for request in self.active_requests:
            if request.id == request_id:
                return request
        for request in self.finished_requests:
            if request.id == request_id:
                return request
        if request_id == consts.MPI_REQUEST_NULL:
            return None
        assert not raise_error, "Request not found"
        return None

    def get_request_index(self, request_id):
        if request_id == consts.MPI_REQUEST_NULL:
            return -1
        for i, request in enumerate(self.active_requests):
            if request.id == request_id:
                return i
        return -1

    def get_persistent_request(self, request_id):
        for request in self.persistent_requests:
            if request.id == request_id:
                return request
        return None

    def remove_persistent_request(self, request):
        self.persistent_requests = copy.copy(self.persistent_requests)
        self.persistent_requests.remove(request)

    def add_collective_request(self, context, comm, cc_id):
        request_id = self.new_request_id(Request.TYPE_COLLECTIVE)
        request = CollectiveRequest(request_id, comm, cc_id)
        self.add_request(request)
        context.event.new_request = request_id
        if context.gcontext.worker.send_protocol == "full":
            context.event.cc = (comm.comm_id, cc_id, comm.group.size)
        return request_id

    def reset_state(self):
        self.status = None
        self.tested_request_ids = None
        self.tested_requests_pointer = None
        self.tested_requests_status_ptr = None
        self.flag_ptr = None
        self.index_ptr = None
        self.probe_data = None
        self.immediate_wait = False

    def are_tested_requests_finished(self):
        if not self.tested_request_ids:
            return True
        for request_id in self.tested_request_ids:
            if request_id == consts.MPI_REQUEST_NULL:
                continue
            for request in self.finished_requests:
                if request.id == request_id:
                    break
            else:
                return False
        return True

    def waits_for_single_non_null_request(self):
        flag = False
        for request_id in self.tested_request_ids:
            if request_id != consts.MPI_REQUEST_NULL:
                if not flag:
                    flag = True
                else:
                    return False
        return True

    def index_of_first_non_null_request(self):
        for i, request_id in enumerate(self.tested_request_ids):
            if request_id != consts.MPI_REQUEST_NULL:
                return i
        assert False  # This should not happen

    def set_ready(self):
        self.reset_state()
        self.status = self.StatusReady

    def set_probe(self, comm, source, tag, flag_ptr, status_ptr):
        self.reset_state()
        self.status = self.StatusProbe
        self.flag_ptr = flag_ptr
        self.probe_data = (comm.comm_id, source, tag, status_ptr)

    def set_wait(self,
                 request_ids,
                 request_ptr=None,
                 status_ptr=None,
                 status=None,
                 index_ptr=None,
                 immediate=False):
        assert request_ids
        self.reset_state()
        # This wait was called immediately after creating request,
        # hence buffers are not locked
        self.immediate_wait = immediate
        if status:
            self.status = status
        else:
            self.status = self.StatusWaitAll
        if index_ptr:
            self.index_ptr = index_ptr
        assert request_ids
        self.tested_request_ids = request_ids
        self.tested_requests_pointer = request_ptr
        self.tested_requests_status_ptr = status_ptr

    def set_finished(self):
        self.reset_state()
        self.status = self.StatusFinished

    def set_test(self, request_ids, flag_ptr, request_ptr, status_ptr):
        assert request_ids
        self.reset_state()
        self.status = self.StatusTest
        self.flag_ptr = flag_ptr
        self.tested_request_ids = request_ids
        self.tested_requests_pointer = request_ptr
        self.tested_requests_status_ptr = status_ptr

    def find_deterministic_match(self):
        for i, r in enumerate(self.active_requests):
            if not r.is_receive() or r.source == consts.MPI_ANY_SOURCE:
                continue
            for j in xrange(i):
                s = self.active_requests[j]
                if s.is_receive() and r.is_suppressed_by(s):
                    break
            else:
                pid = r.comm.group.rank_to_pid(r.source)
                for s in self.gstate.states[pid].active_requests:
                    if not s.is_send() or s.comm.comm_id != r.comm.comm_id:
                        continue
                    if s.comm.group.rank_to_pid(s.target) == self.pid and \
                            (r.tag == s.tag or
                             r.tag == consts.MPI_ANY_TAG):
                        return ((pid, s, self.pid, r))

    def probe_is_possible(self, comm_id, rank, tag):
        for request in self.active_requests:
            if not request.is_receive():
                continue
            if (request.source == consts.MPI_ANY_SOURCE
                    or request.source == rank) \
                    and (request.tag == tag or
                         request.tag == consts.MPI_ANY_TAG) \
                    and (request.comm.comm_id == comm_id):
                return False
        return True

    def find_nondeterministic_matches(self):
        results = []
        for i, r in enumerate(self.active_requests):
            if not r.is_receive() or r.source != consts.MPI_ANY_SOURCE:
                continue
            for j in xrange(i):
                s = self.active_requests[j]
                if s.is_receive() and r.is_suppressed_by(s):
                    break
            else:
                for state in self.gstate.states:
                    for s in state.active_requests:
                        if not s.is_send() or s.comm.comm_id != r.comm.comm_id:
                            continue
                        if s.comm.group.rank_to_pid(s.target) == self.pid and \
                                (r.tag == s.tag or
                                 r.tag == consts.MPI_ANY_TAG):
                            results.append((state.pid, s, self.pid, r))
                            break
        return results

    def probe_nondeterministic(self, comm_id, tag):
        results = []
        for state in self.gstate.states:
            for s in state.active_requests:
                if not s.is_send() or s.comm.comm_id != comm_id:
                    continue
                if s.comm.group.rank_to_pid(s.target) == self.pid and \
                        (tag == s.tag or
                         tag == consts.MPI_ANY_TAG) and \
                        self.probe_is_possible(comm_id, s.target, s.tag):
                    results.append((state.pid, s))
                    break
        return results

    def probe_deterministic(self, comm_id, source, tag):
        pid = self.get_comm(comm_id).group.rank_to_pid(source)
        for s in self.gstate.states[pid].active_requests:
            if not s.is_send() or s.comm.comm_id != comm_id:
                continue
            if s.comm.group.rank_to_pid(s.target) == self.pid and \
                    (tag == s.tag or
                     tag == consts.MPI_ANY_TAG) and \
                    self.probe_is_possible(comm_id, s.target, s.tag):
                return (pid, s)

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
        for request in self.active_requests:
            if request.is_data_addr(addr):
                return request.stacktrace
        for request in self.finished_requests:
            if request.is_data_addr(addr):
                return request.stacktrace

    def mpi_leak_check(self, generator, node):
        for request in self.active_requests:
            context = generator.make_context(node, self)
            if request.is_send():
                source = request.comm.group.pid_to_rank(self.pid)
                e = errormsg.NotReceivedMessage(context,
                                                source=source,
                                                target=request.target,
                                                tag=request.tag)
            else:
                e = errormsg.NotFreedRequest(context,
                                             request_name=request.name)
            context.add_error_message(e)
        for request in self.finished_requests:
            context = generator.make_context(node, self)
            e = errormsg.NotFreedRequest(context,
                                         request_name=request.name)
            context.add_error_message(e)

    def get_indices_of_tested_and_finished_requests(self):
        result = []
        for i, request_id in enumerate(self.tested_request_ids):
            for request in self.finished_requests:
                if request.id == request_id:
                    result.append(i)
                    break
        return result

    def finish_send_request(self, request):
        self.active_requests = copy.copy(self.active_requests)
        self.active_requests.remove(request)
        if request.send_type != Request.TYPE_SEND_RENDEZVOUS:
            request.dec_ref()
        else:
            self.add_finished_request(request)

    def finish_receive_request(self, request, rank, tag, vg_buffer):
        self.active_requests = copy.copy(self.active_requests)
        self.active_requests.remove(request)
        self.add_finished_request(
            request.make_finished_request(rank, tag, vg_buffer))

    def finish_collective_request(self, request):
        self.active_requests = copy.copy(self.active_requests)
        self.active_requests.remove(request)
        self.add_finished_request(request)

    def remove_finished_request(self, request):
        request.dec_ref()
        self.finished_requests = copy.copy(self.finished_requests)
        self.finished_requests.remove(request)

    def set_probe_promise(self, comm_id, source, tag, rank):
        self.probe_promise = (comm_id, source, tag, rank)

    def get_probe_promise(self, comm_id, source, tag):
        if self.probe_promise is None:
            return None
        c, s, t, rank = self.probe_promise
        if c == comm_id and s == source and t == tag:
            return rank

    def new_request_id(self, request_type):
        c = Request.TYPES_COUNT * self.gstate.process_count
        i = c + Request.TYPES_COUNT * self.pid + request_type
        while True:
            for request in self.active_requests:
                if i == request.id:
                    break
            else:
                for request in self.finished_requests:
                    if i == request.id:
                        break
                else:
                    for request in self.persistent_requests:
                        if i == request.id:
                            break
                    else:
                        return i
            i += c

    def collect_buffers(self, lst):
        for request in self.active_requests:
            request.collect_buffers(lst)
        for request in self.finished_requests:
            request.collect_buffers(lst)
        for request in self.persistent_requests:
            request.collect_buffers(lst)

    def __repr__(self):
        info = ""
        if self.vg_state is None:
            info = " no_vg_state"
        return "<state {0:x} pid={1}{2}>".format(id(self), self.pid, info)
