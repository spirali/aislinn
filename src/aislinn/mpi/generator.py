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
from base.utils import convert_type
import consts
import mpicalls
import event
import ops
import base.resource

import logging
import sys
import datetime

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


class Generator:

    # TODO: Universal architecture detection
    POINTER_SIZE = 8
    INT_SIZE = 4
    STATUS_SIZE = 3 * INT_SIZE
    REQUEST_SIZE = INT_SIZE

    def __init__(self, args, valgrind_args, aislinn_args):
        self.args = args
        self.controller = base.controller.Controller(args)
        self.controller.valgrind_args = valgrind_args
        if aislinn_args.debug_under_valgrind:
            self.controller.debug_under_valgrind = True
        if aislinn_args.profile_under_valgrind:
            self.controller.profile_under_valgrind = True
        self.statespace = StateSpace()
        self.fatal_error = False
        self.initial_node = None
        self.process_count = None
        self.working_queue = deque()
        self.error_messages = []
        self.message_sizes = set()
        self.vg_states = base.resource.ResourceManager("vg_state")
        self.vg_buffers = base.resource.ResourceManager("vg_buffer")

        self.vg_state_cache = {}

        self.send_protocol = aislinn_args.send_protocol
        self.send_protocol_eager_threshold = \
                aislinn_args.send_protocol_eager_threshold
        self.send_protocol_randezvous_threshold = \
                aislinn_args.send_protocol_randezvous_threshold

        self.init_time = None
        self.end_time = None

        if aislinn_args.stats:
            self.statistics_tick = aislinn_args.stats
            self.statistics = []
        else:
            self.statistics_tick = None
            self.statistics = None

        self.search = aislinn_args.search
        self.max_states = aislinn_args.max_states
        self.debug_state = aislinn_args.debug_state
        self.is_full_statespace = False

    def get_statistics(self):
        if self.statistics is None:
            return None
        else:
            return ([ ("Length of working queue", "states"),
                      ("All pages", "pages"),
                      ("Active pages", "pages"),
                      ("Sum of buffer sizes", "bytes") ],
                    self.statistics,
                    self.statistics_tick)

    def record_statistics(self):
        stats = self.controller.get_stats()
        self.statistics.append((
            len(self.working_queue),
            stats["pages"],
            stats["active-pages"],
            stats["buffers-size"]))

    def add_error_message(self, error_message):
        if error_message.name in [ e.name for e in self.error_messages]:
            return
        self.error_messages.append(error_message)

    def add_error_messages(self, error_messages):
        for error_message in error_messages:
            self.add_error_message(error_message)

    def initial_execution(self, result):
        while True:
            result = result.split()
            if result[0] == "EXIT":
                e = errormsg.ErrorMessage()
                e.name = "nompicall"
                e.short_description = "No MPI routine"
                e.description = "Program terminated without calling MPI_Init"
                self.add_error_message(e)
                return True
            elif result[0] == "REPORT":
                e = self.make_error_message_from_report(result)
                self.add_error_message(e)
                return True
            elif result[1] == "MPI_Initialized":
                assert len(result) == 3
                ptr = convert_type(result[2], "ptr")
                self.controller.write_int(ptr, 0)
                result = self.controller.run_process()
                continue
            elif result[1] != "MPI_Init":
                e = errormsg.ErrorMessage()
                e.name = "nompiinit"
                e.short_description = "MPI is not initialized"
                e.description = "{0} was called without MPI_Init".format(result[1])
                self.add_error_message(e)
                return True
            break

        function_ptrs = result[4:] # skip CALL MPI_Init argc argv

        # The order of the ops is important!
        operations = [ consts.MPI_SUM,
                    consts.MPI_PROD,
                    consts.MPI_MINLOC,
                    consts.MPI_MAXLOC ]
        assert len(function_ptrs) == \
               len(ops.buildin_operations) == len(operations)

        for ptr, op_id in zip(function_ptrs, operations):
            ops.buildin_operations[op_id].fn_ptr = ptr

        vg_state = self.save_state(True)

        if self.send_protocol == "dynamic":
            send_protocol_thresholds = (0, sys.maxint)
        else:
            send_protocol_thresholds = None

        gstate = GlobalState(vg_state,
                             self.process_count,
                             send_protocol_thresholds)
        vg_state.dec_ref()
        assert vg_state.ref_count == self.process_count

        self.initial_node = self.add_node(None, gstate, True)
        self.statespace.initial_node = self.initial_node
        return False

    def run(self, process_count):
        self.init_time = datetime.datetime.now()
        self.process_count = process_count
        result = self.controller.start()
        if result is None:
            return False
        try:
            if self.initial_execution(result):
                return True
            tick = self.statistics_tick
            tick_counter = tick
            while self.working_queue:
                if self.search == "dfs":
                    node, gstate = self.working_queue.pop()
                else: # bfs
                    node, gstate = self.working_queue.popleft()
                self.expand_node(node, gstate)
                if self.fatal_error:
                    return True
                self.cleanup()

                if tick:
                    tick_counter -= 1
                    if tick_counter == 0:
                        tick_counter = tick
                        self.record_statistics()

                if self.statespace.nodes_count > self.max_states:
                    logging.info("Maximal number of states reached")
                    return True

            self.final_check()
            self.is_full_statespace = True
        finally:
            self.controller.kill()
            self.end_time = datetime.datetime.now()
        return True

    def final_check(self):
        # Check there is no memory leak
        assert self.vg_states.resource_count == 0
        assert self.vg_buffers.resource_count == 0
        assert len(self.vg_state_cache) == 0
        stats = self.controller.get_stats()
        # All pages are active, i.e. we have freed everyhing else
        assert stats["pages"] == stats["active-pages"]
        assert stats["buffers-size"] == 0

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

    def write_status(self, status_ptr, source, tag, size):
        self.controller.write_ints(status_ptr, [ source, tag, size ])

    def apply_matching(self, node, state, matching):
        for request, message in matching:
            assert not request.is_receive() or \
                   message is not None or \
                   request.source == consts.MPI_PROC_NULL
            state.set_request_as_completed(request, message)
            """
            if request.pointer is not None:
                self.controller.write_int(request.pointer,
                                          consts.MPI_REQUEST_NULL)
            if request.is_receive() \
               and request.source == consts.MPI_PROC_NULL \
               and request.status_ptr:
                self.write_status(request.status_ptr,
                                  consts.MPI_PROC_NULL,
                                  consts.MPI_ANY_TAG,
                                  0)
            """
            if message:
                """
                if request.status_ptr:
                    self.write_status(request.status_ptr,
                                      message.source,
                                      message.tag,
                                      message.size)
                """
                count = request.datatype.get_count(message.size)
                if count is None:
                    # This should never happen because
                    # datatype check should be already performed
                    raise Exception("Internal error")
                if count > request.count:
                    e = errormsg.ErrorMessage()
                    e.node = node
                    e.name = "message-truncated"
                    e.short_description = "Message truncated"
                    e.description = "Message is bigger than receive buffer"
                    e.pid = state.pid
                    self.add_error_message(e)
                    self.fatal_error = True
                    # TODO: In fact it is not fatal error, it should be handle
                    # in a way that we can continue
                    return False
                request.datatype.unpack(self.controller,
                                        message.vg_buffer,
                                        count,
                                        request.data_ptr)
                state.remove_message(message)
            if request.is_collective():
                op = state.gstate.get_operation_by_cc_id(request.comm_id,
                                                         request.cc_id)
                op.complete(self, state)
        return True

    def fast_partial_expand(self, node, gstate):
        for state in gstate.states:
            if state.status == State.StatusWaitAll or \
                    state.status == State.StatusWaitAny:
                if not state.are_requests_deterministic():
                    continue
                matches = state.check_requests(upto_active=True)
                len(matches) == 1 # Active request are deterministic here

                if not matches[0]:
                    continue

                logging.debug("Fast partial expand pid=%s", state.pid)

                self.controller.restore_state(state.vg_state.id)

                if not self.apply_matching(node, state, matches[0]):
                    return False

                state.vg_state.dec_ref()
                state.vg_state = self.save_state(True)
                new_node = self.add_node(node, gstate)
                node.add_arc(Arc(new_node, ()))
                return True
        return False

    def fast_expand_node(self, node, gstate):
        partial_found = False
        for state in gstate.states:
            if state.status == State.StatusWaitAll or \
                    state.status == State.StatusWaitAny:
                if not state.are_requests_deterministic():
                    continue
                matches = state.check_requests(upto_active=True)
                len(matches) == 1 # Active request are deterministic here

                if not state.is_matching_covering_active_requests(matches[0]):
                   partial_found = True
                   continue

                if state.status == State.StatusWaitAny:
                    if len(state.active_request_ids) > 1:
                        # We cannot continue because we need branch,
                        # so the best we can hope
                        # for is "partial_found"
                        continue
                    assert len(state.active_request_ids) == 1
                    self.controller.write_int(state.index_ptr, 1)

                logging.debug("Fast expand status=wait pid=%s", state.pid)
                self.controller.restore_state(state.vg_state.id)
                if not self.apply_matching(node, state, matches[0]):
                    return False
                state.finish_active_requests(self)
                self.execute_state_and_add_node(node, state)
                return True

            if state.status == State.StatusReady:
                logging.debug("Fast expand status=init pid=%s", state.pid)
                self.controller.restore_state(state.vg_state.id)
                self.execute_state_and_add_node(node, state)
                return True
        if partial_found:
            return self.fast_partial_expand(node, gstate)
        return False

    def fork_standard_sends(self, node, gstate):
        new_state_created = False
        for state in gstate.states:
            if state.status == State.StatusWaitAll or \
                    state.status == State.StatusTest or \
                    state.status == State.StatusWaitAny:
                requests = state.fork_standard_sends()
                if requests is None:
                    continue
                logging.debug("Forking because of standard send {0}", requests)
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
                    new_state = new_gstate.get_state(state.pid)

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
            if state.status == State.StatusWaitAll:
                self.process_wait_or_test_all(node, state, False)
            elif state.status == State.StatusWaitAny:
                self.process_wait_or_test_any(node, state, False)
            elif state.status == State.StatusTest:
                self.process_wait_or_test_all(node, state, True)
            elif state.status == State.StatusProbe:
                self.process_probe(node, state)
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

    def restore_state(self, state):
        # TODO: Use in code of generator
        self.controller.restore_state(state.vg_state.id)

    def process_probe(self, node, state):
        # TODO: Move deterministic (no ANY_SOURCE or flag=0) probe into fast expand

        comm_id, source, tag, flag_ptr, status_ptr = state.probe_data

        for request in state.requests:
            if request is not None and \
                    request.is_receive() and \
                    request.comm_id == comm_id:
                raise Exception("Probe with pending recv request in the same"
                                "communicator is not supported now. Sorry")
                # TODO: To make it correct, we need finish all compatible recv
                # first

        messages, already_probed = state.probe_messages(comm_id, source, tag)

        if flag_ptr is not None and not already_probed: # It is Iprobe
            new_gstate = state.gstate.copy()
            new_state = new_gstate.get_state(state.pid)
            self.controller.restore_state(new_state.vg_state.id)
            self.controller.write_int(flag_ptr, 0)
            self.execute_state_and_add_node(node, new_state)
            if status_ptr:
                # TODO: Set status as undefined
                pass

        for message in messages:
            new_gstate = state.gstate.copy()
            new_state = new_gstate.get_state(state.pid)
            self.controller.restore_state(new_state.vg_state.id)
            if flag_ptr is not None:
                self.controller.write_int(flag_ptr, 1)
            if status_ptr:
                self.write_status(status_ptr,
                                  message.source,
                                  message.tag,
                                  message.size)
            new_state.add_probed_message(comm_id, source, tag, message)
            self.execute_state_and_add_node(node, new_state)

    def process_wait_or_test_all(self, node, state, test):
        if test:
            new_gstate = state.gstate.copy()
            new_state = new_gstate.get_state(state.pid)
            self.controller.restore_state(new_state.vg_state.id)
            self.controller.write_int(state.flag_ptr, 0)
            self.execute_state_and_add_node(node, new_state)

        matches = state.check_requests()
        logging.debug("Wait or test all: len(matches)=%s pid=%s",
                len(matches), state.pid)
        for matching in matches:
            covered = state.is_matching_covering_active_requests(matching)
            if not covered and not any(r.is_receive() for r, m in matching):
                # Not all request is completed and no new receive request
                # matched so there is no reason to create new state
                continue
            new_gstate = state.gstate.copy()
            new_state = new_gstate.get_state(state.pid)
            self.controller.restore_state(new_state.vg_state.id)
            if not self.apply_matching(node, new_state, matching):
                return
            if not covered:
                # Not all active requests are ready, so just apply matchings
                # and create new state
                new_state.vg_state.dec_ref()
                new_state.vg_state = self.save_state(True)
                new_node = self.add_node(node, new_gstate)
                node.add_arc(Arc(new_node, ()))
                return
            new_state.finish_active_requests(self)
            if test:
                self.controller.write_int(state.flag_ptr, 1)
            self.execute_state_and_add_node(node, new_state)

    def process_wait_or_test_any(self, node, state, test):
        #if test:
        #    new_gstate = state.gstate.copy()
        #    new_state = new_gstate.get_state(state.pid)
        #    new_state.reinit_active_requests()
        #    self.controller.restore_state(new_state.vg_state.id)
        #    self.controller.write_int(state.flag_ptr, 0)
        #    self.execute_state_and_add_node(node, new_state)

        matches = state.check_requests()
        logging.debug("Wait or test any: len(matches)=%s pid=%s",
                len(matches), state.pid)
        for matching in matches:
            for i, request in \
                state.active_requests_covered_by_matching(matching):

                new_gstate = state.gstate.copy()
                new_state = new_gstate.get_state(state.pid)
                self.controller.restore_state(new_state.vg_state.id)

                if not self.apply_matching(node, new_state, matching):
                    return
                self.controller.write_int(state.index_ptr, i)

                # We need to refresh request, from new state
                request = new_state.get_request(request.id)
                new_state.finish_active_request(self, request)
                #if test:
                #    self.controller.write_int(state.flag_ptr, 1)
                self.execute_state_and_add_node(node, new_state)


    def execute_state_and_add_node(self, node, state):
        context = self.execute_state(state)
        new_node = self.add_node(node, state.gstate)
        arc = Arc(new_node, context.events)
        node.add_arc(arc)
        if context.error_messages is not None:
            for e in context.error_messages:
                e.node = node
                e.last_arc = arc
                e.pid = state.pid
            self.add_error_messages(context.error_messages)

    def save_state(self, make_hash):
        if make_hash:
            hash = self.controller.hash_state()
            vg_state = self.vg_state_cache.get(hash)
            if vg_state:
                logging.debug("State %s retrieved from cache", hash)
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
        e = errormsg.make_runtime_err(parts[1], parts[2:])
        e.stacktrace = self.controller.get_stacktrace()
        return e

    def execute_state(self, state):
        if state.vg_state is not None:
            state.vg_state.dec_ref()
            state.vg_state = None
        context = ExecutionContext()
        try:
            while True:
                call = self.controller.run_process().split()
                if call[0] == "EXIT":
                    exitcode = convert_type(call[1], "int")
                    e = event.ExitEvent("Exit", state.pid, exitcode)
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
                call_class = mpicalls.calls.get(call[1])
                if call_class is not None:
                    if call_class.run(self, call[2:], state, context):
                        break
                else:
                    raise Exception("Unkown function call: " + repr(call))
        except errormsg.ExecutionError as e:
            logging.debug("ExecutionError: %s", e.error_message)
            error_message = e.error_message
            error_message.stacktrace = self.controller.get_stacktrace()
            error_message.function_name = call[1]
            context.add_error_message(error_message)
            # TODO: It is not necessary to stop everything, just expansion of
            # this state
            self.fatal_error = True
        state.vg_state = self.save_state(True)
        return context

    def add_call_event(self, context, event):
        stacktrace = self.controller.get_stacktrace()
        event.stacktrace = stacktrace
        context.add_event(event)

    def new_buffer(self, size):
        buffer_id = self.controller.new_buffer(size)
        vg_buffer = self.vg_buffers.new(buffer_id)
        return vg_buffer

    def new_buffer_and_pack(self, datatype, count, addr):
        vg_buffer = self.new_buffer(datatype.size * count)
        datatype.pack(self.controller, addr, vg_buffer, count)
        vg_buffer.hash = self.controller.hash_buffer(vg_buffer.id)
        return vg_buffer

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

        uids = ",".join([ str(state.vg_state.id) if state.vg_state is not None else "F"
                 for state in gstate.states ])
        #uids += [ [ m.vg_buffer.id for m in s.messages ] for s in gstate.states ]

        node = Node(uids, hash)
        if prev:
            node.prev = prev
        self.statespace.add_node(node)
        self.working_queue.append((node, gstate))

        if self.debug_state == uids:
            e = errormsg.ErrorMessage()
            e.node = node
            e.name = "captured-state"
            e.short_description = "Captured state"
            e.description = "The state {0} was captured " \
                            "because of option --debug-state".format(uids)
            self.add_error_message(e)
            self.fatal_error = True
            return node
        return node

    def create_report(self):
        for error_message in self.error_messages:
            error_message.events = \
                    self.statespace.events_to_node(error_message.node,
                                                   error_message.last_arc)
        return Report(self)
