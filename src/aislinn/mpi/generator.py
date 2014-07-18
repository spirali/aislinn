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


import base.controller
import errormsg
from state import State
from base.node import Node, Arc
from base.statespace import StateSpace
from collections import deque
from globalstate import GlobalState
from base.report import Report
from base.utils import convert_types
import consts

import event
import base.resource
import logging
import sys
import types

class ExecutionContext:

    def __init__(self):
        self.events = []
        self.error_messages = None

    def add_event(self, event):
        self.events.append(event)

    def add_error_message(self, error_message):
        if self.error_messages is None:
            self.error_messages = []
        self.error_messages.append(error_message)

class ValidateException(Exception):

    def __init__(self, value, arg_position):
        Exception.__init__(self)
        self.value = value
        self.arg_position = arg_position


class Generator:

    def __init__(self, args, valgrind_args, aislinn_args):
        self.args = args
        self.controller = base.controller.Controller(args)
        self.controller.valgrind_args = valgrind_args
        self.statespace = StateSpace()
        self.fatal_error = False
        self.initial_node = None
        self.process_count = None
        self.working_queue = deque()
        self.error_messages = []
        self.calls = {
                "MPI_Comm_rank" : self.call_MPI_Comm_rank,
                "MPI_Comm_size" : self.call_MPI_Comm_size,
                "MPI_Send" : self.call_MPI_Send,
                "MPI_Recv" : self.call_MPI_Recv,
                "MPI_Isend" : self.call_MPI_ISend,
                "MPI_Irecv" : self.call_MPI_IRecv,
                "MPI_Wait" : self.call_MPI_Wait,
                "MPI_Test" : self.call_MPI_Test,
                "MPI_Waitall" : self.call_MPI_Waitall
        }

        self.vg_states = base.resource.ResourceManager("vg_state")
        self.vg_buffers = base.resource.ResourceManager("vg_buffer")

        self.vg_state_cache = {}

        self.send_protocol = aislinn_args.send_protocol
        self.send_protocol_eager_threshold = \
                aislinn_args.send_protocol_eager_threshold
        self.send_protocol_randezvous_threshold = \
                aislinn_args.send_protocol_randezvous_threshold

    def add_error_message(self, error_message):
        if error_message.name in [ e.name for e in self.error_messages]:
            return
        self.error_messages.append(error_message)

    def add_error_messages(self, error_messages):
        for error_message in error_messages:
            self.add_error_message(error_message)

    def run(self, process_count):
        self.process_count = process_count
        result = self.controller.start()
        if result is None:
            return False
        try:
            result = result.split()
            if result[0] == "EXIT":
                e = errormsg.ErrorMessage()
                e.name = "nompicall"
                e.short_description = "No MPI routine"
                e.description = "Program terminated without calling MPI routine"
                self.add_error_message(e)
                return True
            elif result[0] == "REPORT":
                e = self.make_error_message_from_report(result)
                self.add_error_message(e)
                return True
            elif result[1] != "MPI_Init":
                raise Exception("MPI_Init is not called")

            vg_state = self.save_state(True)

            states = []
            for i in xrange(process_count):
                vg_state.inc_ref()
                state = State(i, vg_state)
                states.append(state)
            vg_state.dec_ref()
            assert vg_state.ref_count == process_count

            if self.send_protocol == "dynamic":
                send_protocol_thresholds = (0, sys.maxint)
            else:
                send_protocol_thresholds = None

            gstate = GlobalState(states, send_protocol_thresholds)
            self.initial_node = self.add_node(None, gstate, True)
            self.statespace.initial_node = self.initial_node

            while self.working_queue:
                node, gstate = self.working_queue.popleft()
                self.expand_node(node, gstate)
                if self.fatal_error:
                    return True
                self.cleanup()

            # Check there is no memory leak
            assert self.vg_states.resource_count == 0
            assert self.vg_buffers.resource_count == 0
            assert len(self.vg_state_cache) == 0
        finally:
            self.controller.kill()
        return True

    def cleanup(self):
        if self.vg_states.not_used_resources:
            vg_states = self.vg_states.pickup_resources_to_clean()
            for vg_state in vg_states:
                if vg_state.hash:
                    del self.vg_state_cache[vg_state.hash]
                self.controller.free_state(vg_state.id)

        if self.vg_buffers.not_used_resources:
            vg_buffers = self.vg_buffers.pickup_resources_to_clean()
            for vg_buffer in vg_buffers:
                self.controller.free_buffer(vg_buffer.id)

    def apply_matching(self, state, matching):
        for request, message in matching:
            assert not request.is_receive() or message is not None
            state.set_request_as_completed(request)
            if message:
                self.controller.write_buffer(request.data_ptr,
                                             message.vg_buffer.id)
                state.remove_message(message)

    def fast_expand_node(self, node, gstate):
        for state in gstate.states:
            if state.status == State.StatusWait:
                if not state.are_requests_deterministic():
                    continue
                matches = state.check_requests(gstate, upto_active=True)
                len(matches) == 1 # Active request are deterministic here

                if not state.is_matching_covers_active_requests(matches[0]):
                    continue

                logging.debug("Fast expand status=wait rank=%s", state.rank)
                self.controller.restore_state(state.vg_state.id)
                self.apply_matching(state, matches[0])
                state.remove_active_requests()
                self.execute_state_and_add_node(node, gstate, state)
                return True

            if state.status == State.StatusInited:
                logging.debug("Fast expand status=init rank=%s", state.rank)
                self.controller.restore_state(state.vg_state.id)
                self.execute_state_and_add_node(node, gstate, state)
                return True
        return False

    def fork_standard_sends(self, node, gstate):
        new_state_created = False
        for state in gstate.states:
            if state.status == State.StatusWait or \
                    state.status == State.StatusTest:
                requests = state.fork_standard_sends(gstate)
                if requests is None:
                    continue
                for buffered, synchronous in requests:
                    if self.send_protocol == "dynamic":
                       eager_threshold, randezvous_threshold = \
                               gstate.send_protocol_thresholds
                       assert eager_threshold <= randezvous_threshold
                       if buffered:
                           buffered_size = \
                               max(max(r.message.size for r in buffered),
                                   eager_threshold)
                       else:
                           buffered_size = eager_threshold

                       if synchronous:
                           synchronous_size = \
                               min(min(r.message.size for r in synchronous),
                                   randezvous_threshold)
                       else:
                           synchronous_size = randezvous_threshold

                       if buffered_size >= randezvous_threshold or \
                               synchronous_size < eager_threshold:
                           continue

                    new_gstate = gstate.copy()
                    new_state = new_gstate.get_state(state.rank)

                    if self.send_protocol == "dynamic":
                       new_gstate.send_protocol_thresholds = (buffered_size,
                                                              synchronous_size)

                    for r in buffered:
                        new_state.set_request_as_completed(r)
                    for r in synchronous:
                        new_state.set_request_as_synchronous(r)
                    new_node = self.add_node(node, new_gstate)
                    node.add_arc(Arc(new_node, ()))
                    new_state_created = True
                if new_state_created:
                    return True
        return False

    def expand_node(self, node, gstate):
        logging.debug("Expanding node %s", node.uid)

        if self.fast_expand_node(node, gstate):
            # Do not dispose state because we have reused gstate
            return

        if self.fork_standard_sends(node, gstate):
            gstate.dispose()
            return

        for state in gstate.states:
            if state.status == State.StatusWait:
                self.process_wait_or_test(node, gstate, state, False)
            elif state.status == State.StatusTest:
                self.process_wait_or_test(node, gstate, state, True)
            elif state.status == State.StatusFinished:
                continue
            else:
                raise Exception("Unknown status")

        if not node.arcs and \
                any(state.status != State.StatusFinished
                    for state in gstate.states):
            message = errormsg.Deadlock()
            message.node = node
            self.add_error_message(message)

        gstate.dispose()

    def process_wait_or_test(self, node, gstate, state, test):
        if test:
            new_gstate = gstate.copy()
            new_state = new_gstate.get_state(state.rank)
            self.controller.restore_state(new_state.vg_state.id)
            self.controller.write_int(state.flag_ptr, 0)
            self.execute_state_and_add_node(node, new_gstate, new_state)

        matches = state.check_requests(gstate)
        logging.debug("Wait or test len(matches)=%s rank=%s",
                len(matches), state.rank)
        for matching in matches:
            covered = state.is_matching_covers_active_requests(matching)
            if not covered and not any(r.is_receive() for r, m in matching):
                # Not all request is completed and no new receive request
                # matched so there is no reason to create new state
                continue
            new_gstate = gstate.copy()
            new_state = new_gstate.get_state(state.rank)
            self.controller.restore_state(new_state.vg_state.id)
            self.apply_matching(new_state, matching)
            if not covered:
                # Not all active requests are ready, so just apply matchings
                # and create new state
                new_node = self.add_node(node, new_gstate)
                node.add_arc(Arc(new_node, ()))
                return
            new_state.remove_active_requests()
            if test:
                self.controller.write_int(state.flag_ptr, 1)
            self.execute_state_and_add_node(node, new_gstate, new_state)

    def execute_state_and_add_node(self, node, gstate, state):
        context = self.execute_state(gstate, state)
        new_node = self.add_node(node, gstate)
        arc = Arc(new_node, context.events)
        node.add_arc(arc)
        if context.error_messages is not None:
            for e in context.error_messages:
                e.node = node
                e.last_arc = arc
                e.rank = state.rank
            self.add_error_messages(context.error_messages)

    def save_state(self, make_hash):
        if make_hash:
            hash = self.controller.hash_state()
            vg_state = self.vg_state_cache.get(hash)
            if vg_state:
                vg_state.inc_ref()
                return vg_state
        else:
            hash = None

        vg_state = self.vg_states.new(self.controller.save_state())
        vg_state.hash = hash
        self.vg_state_cache[hash] = vg_state
        return vg_state

    def make_error_message_from_report(self, parts):
        assert parts[0] == "REPORT"
        return errormsg.make_runtime_err(parts[1])

    def execute_state(self, gstate, state):
        if state.vg_state is not None:
            state.vg_state.dec_ref()
            state.vg_state = None
        context = ExecutionContext()
        try:
            while True:
                call = self.controller.run_process().split()
                if call[0] == "EXIT":
                    exitcode = int(call[1])
                    e = event.ExitEvent("Exit", state.rank, exitcode)
                    context.add_event(e)
                    state.set_finished()
                    if exitcode != 0:
                        context.add_error_message(
                                errormsg.NonzeroExitCode(exitcode))
                    return context
                if call[0] == "REPORT":
                    context.add_error_message(
                            self.make_error_message_from_report(call))
                    self.fatal_error = True
                    return context
                fn = self.calls.get(call[1])
                if fn is not None:
                    if fn(call[2:], gstate, state, context):
                        break
                else:
                    raise Exception("Unkown function call: " + repr(call))
        except ValidateException as e:
            emsg = errormsg.InvalidArgument(call[1], e.value, e.arg_position)
            emsg.stacktrace = self.controller.get_stacktrace()

            context.add_error_message(emsg)
            # TODO: It is not necessary to stop everything, just expansion of
            # this state
            self.fatal_error = True

        state.vg_state = self.save_state(True)
        return context

    def add_call_event(self, context, event):
        stacktrace = self.controller.get_stacktrace()
        event.stacktrace = stacktrace
        context.add_event(event)

    def validate_rank(self,
                      rank,
                      arg_position,
                      any_source_allowed):

        if rank == consts.MPI_ANY_SOURCE:
            if not any_source_allowed:
                raise ValidateException("MPI_ANY_SOURCE", arg_position)
        elif rank < 0 or rank >= self.process_count:
            raise ValidateException(rank, arg_position)

    def validate_count(self, size, arg_position):
        if size < 0:
            raise ValidateException(size, arg_position)

    def get_datatype_size(self, datatype, arg_position):
        size = types.get_datatype_size(datatype)
        if size is None:
            raise ValidateException(datatype, arg_position)
        return size

    def validate_request_ids(self, state, request_ids):
        for request_id in request_ids:
            if not state.is_request_id_valid(request_id):
                raise Exception("Invalid request id {0}, rank {1} ({2})"
                        .format(request_id, state.rank, state.requests))

    def make_send_request(self, gstate, state, message):
        if self.send_protocol == "randezvous":
            return state.add_synchronous_send_request(message)
        elif self.send_protocol == "eager":
            return state.add_completed_request()
        elif self.send_protocol == "dynamic":
            eager_threshold, randezvous_threshold = \
                    gstate.send_protocol_thresholds
            if message.size < eager_threshold:
                return state.add_completed_request()
            elif message.size >= randezvous_threshold:
                return state.add_synchronous_send_request(message)
            else:
                return state.add_standard_send_request(message)
        elif self.send_protocol == "threshold":
            print message.size
            if message.size < self.send_protocol_eager_threshold:
                return state.add_completed_request()
            elif message.size >= self.send_protocol_randezvous_threshold:
                return state.add_synchronous_send_request(message)
            else:
                return state.add_standard_send_request(message)
        else:
            assert self.send_protocol == "full"
            return state.add_standard_send_request(message)


    def call_MPI_Comm_rank(self, args, gstate, state, context):
        assert len(args) == 2
        self.controller.write_int(args[1], state.rank)
        return False

    def call_MPI_Comm_size(self, args, gstate, state, context):
        assert len(args) == 2
        self.controller.write_int(args[1], self.process_count)
        return False

    def call_MPI_Send(self, args, gstate, state, context):
        buf_ptr, count, datatype, target, tag, comm = \
            convert_types(args,
                          ("ptr", # buf_ptr
                           "int", # count
                           "int", # datatype
                           "int", # target
                           "int", # tag
                           "int", # comm
                          ))
        self.validate_count(count, 2)
        self.validate_rank(target, 4, False)
        size = count * self.get_datatype_size(datatype, 3)
        buffer_id, hash = self.controller.new_buffer(buf_ptr, size, hash=True)
        vg_buffer = self.vg_buffers.new(buffer_id)
        message = gstate.get_state(target).add_message(
                state.rank, target, tag, vg_buffer, size, hash)

        e = event.CommEvent("Send", state.rank, target, tag)
        self.add_call_event(context, e)

        request_ids = (self.make_send_request(gstate, state, message),)
        state.set_wait(request_ids)
        # TODO: Optimization : If message use eager protocol then nonblock
        return True

    def call_MPI_Recv(self, args, gstate, state, context):
        buf_ptr, count, datatype, source, tag, comm = \
            convert_types(args,
                          ("ptr", # buf_ptr
                           "int", # count
                           "int", # datatype
                           "int", # source
                           "int", # tag
                           "int", # comm
                          ))

        self.validate_count(count, 2)
        self.validate_rank(source, 4, True)
        size = count * self.get_datatype_size(datatype, 3)

        e = event.CommEvent("Recv", state.rank, source, tag)
        self.add_call_event(context, e)

        request_ids = (state.add_recv_request(source, tag, buf_ptr, size),)
        state.set_wait(request_ids)
        # TODO: Optimization : If message is already here,
        # then non block and continue
        return True

    def call_MPI_ISend(self, args, gstate, state, context):
        buf_ptr, count, datatype, target, tag, comm, request_ptr = \
            convert_types(args,
                          ("ptr", # buf_ptr
                           "int", # count
                           "int", # datatype
                           "int", # target
                           "int", # tag
                           "int", # comm
                           "ptr", # request_ptr
                          ))
        self.validate_count(count, 2)
        self.validate_rank(target, 4, False)
        size = count * self.get_datatype_size(datatype, 3)

        buffer_id, hash = self.controller.new_buffer(buf_ptr, size, hash=True)
        vg_buffer = self.vg_buffers.new(buffer_id)
        message = gstate.get_state(target).add_message(
                state.rank, target, tag, vg_buffer, size, hash)
        request_id = self.make_send_request(gstate, state, message)
        self.controller.write_int(request_ptr, request_id)

        e = event.CommEvent("Isend", state.rank, target, tag, request_id)
        self.add_call_event(context, e)
        return False

    def call_MPI_IRecv(self, args, gstate, state, context):
        buf_ptr, count, datatype, source, tag, comm, request_ptr = \
            convert_types(args,
                          ("ptr", # buf_ptr
                           "int", # count
                           "int", # datatype
                           "int", # source
                           "int", # tag
                           "int", # comm
                           "ptr", # request_ptr
                          ))

        self.validate_count(count, 2)
        self.validate_rank(source, 4, True)
        size = count * self.get_datatype_size(datatype, 3)

        request_id = state.add_recv_request(source, tag, buf_ptr, size)
        self.controller.write_int(request_ptr, request_id)

        e = event.CommEvent("Irecv", state.rank, source, tag, request_id)
        self.add_call_event(context, e)
        return False

    def call_MPI_Wait(self, args, gstate, state, context):
        request_ptr, status_ptr = args
        request_ids = [ self.controller.read_int(request_ptr) ]
        self.validate_request_ids(state, request_ids)
        state.set_wait(request_ids)

        e = event.WaitEvent("Wait", state.rank, request_ids)
        self.add_call_event(context, e)
        return True

    def call_MPI_Test(self, args, gstate, state, context):
        request_ptr, flag_ptr, status_ptr = args
        request_ids = [ self.controller.read_int(request_ptr) ]
        self.validate_request_ids(state, request_ids)
        state.set_test(request_ids, flag_ptr)

        e = event.WaitEvent("Test", state.rank, request_ids)
        self.add_call_event(context, e)
        return True

    def call_MPI_Waitall(self, args, gstate, state, context):
        count, requests_ptr, status_ptr = args
        count = int(count)
        request_ids = self.controller.read_ints(requests_ptr, count)
        self.validate_request_ids(state, request_ids)
        state.set_wait(request_ids)

        e = event.WaitEvent("Waitall", state.rank, request_ids)
        self.add_call_event(context, e)
        return True

    def add_node(self, prev, gstate, do_hash=True):
        if do_hash:
            hash = gstate.compute_hash()
            if hash is not None:
                node = self.statespace.get_node_by_hash(hash)
                if node is not None:
                    gstate.dispose()
                    return node
        else:
            hash = None

        uids = [ state.vg_state.id if state.vg_state is not None else "F"
                 for state in gstate.states ]
        #uids += [ [ m.vg_buffer.id for m in s.messages ] for s in gstate.states ]

        node = Node(str(uids), hash)
        if prev:
            node.prev = prev
        self.statespace.add_node(node)
        self.working_queue.append((node, gstate))
        return node

    def create_report(self):
        for error_message in self.error_messages:
            error_message.events = \
                    self.statespace.events_to_node(error_message.node,
                                                   error_message.last_arc)
        return Report(self)
