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


from base.controller import BufferManager
from base.node import Node, Arc
from base.report import Report
from base.statespace import StateSpace
from base.stream import STREAM_STDOUT, STREAM_STDERR
from base.utils import power_set
from collections import deque
from gcontext import GlobalContext
from globalstate import GlobalState
from mpi.context import Context, ErrorFound
from mpi.controller import Controller
from state import State
import consts
import errormsg

import logging
import datetime
import sys


class Generator:

    def __init__(self, args, process_count, valgrind_args, aislinn_args):
        self.args = args
        self.statespace = StateSpace()
        self.consts_pool = None
        self.process_count = process_count
        self.working_queue = deque()
        self.error_messages = []
        self.message_sizes = set()

        self.send_protocol = aislinn_args.send_protocol
        self.send_protocol_eager_threshold = \
                aislinn_args.send_protocol_eager_threshold
        self.send_protocol_rendezvous_threshold = \
                aislinn_args.send_protocol_rendezvous_threshold

        self.init_time = None
        self.end_time = None
        self.deterministic_unallocated_memory = None

        if aislinn_args.stats:
            self.statistics_tick = aislinn_args.stats
            self.statistics = []
        else:
            self.statistics_tick = None
            self.statistics = None

        self.search = aislinn_args.search
        self.max_states = aislinn_args.max_states

        self.stdout_mode = aislinn_args.stdout
        self.stderr_mode = aislinn_args.stderr

        self.debug_state = aislinn_args.debug_state
        if aislinn_args.debug_compare_states:
            self.debug_compare_states = \
                aislinn_args.debug_compare_states.split("~")
            logging.info("debug_compare_states=%s", self.debug_compare_states)
        else:
            self.debug_compare_states = None
        self.debug_captured_states = None
        self.is_full_statespace = False

        self.buffer_manager = BufferManager()
        self.controllers = [ Controller(self.args) for i in xrange(process_count) ]

        for i, controller in enumerate(self.controllers):
            controller.valgrind_args = valgrind_args
            controller.name = i

        if aislinn_args.debug_under_valgrind:
            for controller in self.controllers:
                controller.debug_under_valgrind = True
        if aislinn_args.profile_under_valgrind:
            for controller in self.controllers:
                controller.profile_under_valgrind = True

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
        stats = self._controller.get_stats()
        self.statistics.append((
            len(self.working_queue),
            stats["pages"],
            stats["active-pages"],
            stats["buffers-size"]))

    def add_error_message(self, error_message):
        if error_message.name in [ e.name for e in self.error_messages ]:
            return
        self.error_messages.append(error_message)

    def get_const_ptr(self, id):
        if id == consts.MPI_TAG_UB:
            return self.consts_pool
        raise Exception("Invalid const id")

    def sanity_check(self):
        for node, gstate in self.working_queue:
            gstate.sanity_check()

    def get_controller(self, pid):
        return self.controllers[pid]

    def start_controllers(self):
        # We do actions separately to allow parallel initialization
        for controller in self.controllers:
            controller.start(capture_syscalls=["write"])
        for controller in self.controllers:
            controller.connect()

        initial_node = Node("init", None)
        self.statespace.add_node(initial_node)
        self.statespace.initial_node = initial_node

        if self.send_protocol == "dynamic":
            send_protocol_thresholds = (0, sys.maxint)
        else:
            send_protocol_thresholds = None

        gstate = GlobalState(self.process_count,
                             send_protocol_thresholds)
        gcontext = GlobalContext(self, initial_node, gstate)

        # TODO: Do it in parallel
        for i in xrange(self.process_count):
            context = gcontext.get_context(i)
            if not context.initial_run():
                return False

        gcontext.make_node()
        return True


    def run(self):
        self.init_time = datetime.datetime.now()
        try:
            if not self.start_controllers():
                return False
            tick = self.statistics_tick
            tick_counter = tick
            while self.working_queue:
                if self.search == "dfs":
                    node, gstate = self.working_queue.pop()
                else: # bfs
                    node, gstate = self.working_queue.popleft()
                self.expand_node(node, gstate)
                self.cleanup()

                if tick:
                    tick_counter -= 1
                    if tick_counter == 0:
                        tick_counter = tick
                        self.record_statistics()

                if self.statespace.nodes_count > self.max_states:
                    logging.info("Maximal number of states reached")
                    if self.debug_compare_states is not None:
                        self.debug_compare()
                    return True
            self.memory_leak_check()
            self.final_check()
            self.is_full_statespace = True
        except ErrorFound:
            logging.debug("ErrorFound catched")
        finally:
            for controller in self.controllers:
                controller.kill()
            self.end_time = datetime.datetime.now()
        return True

    def memory_leak_check(self):
        final_nodes = list(self.statespace.all_final_nodes())
        allocations = [ frozenset(node.allocations)
                        if node.allocations else frozenset()
                        for node in final_nodes ]
        all_allocations = frozenset.union(*allocations)
        deterministic = frozenset.intersection(*allocations)
        for a in sorted(all_allocations - deterministic):
            for node in final_nodes:
                if node.allocations and a in node.allocations:
                    gcontext = GlobalContext(self, node, None)
                    m = errormsg.MemoryLeak(gcontext.get_context(a.pid),
                                            address=a.addr,
                                            size=a.size)
                    break
            else:
                assert 0 # This shoud not happen
            self.add_error_message(m)

        self.deterministic_unallocated_memory = 0
        for a in deterministic:
            self.deterministic_unallocated_memory += a.size

    def final_check(self):
        if self.debug_compare_states is not None:
            self.debug_compare()

        for controller in self.controllers:
            controller.make_buffers()
        self.cleanup()

        assert self.buffer_manager.resource_count == 0
        for controller in self.controllers:
            # Check there is no memory leak
            assert controller.states_count == 0
            stats = controller.get_stats()
            # All pages are active, i.e. we have freed everyhing else
            assert stats["pages"] == stats["active-pages"]
            assert stats["buffers-size"] == 0

    def debug_compare(self):
        if self.debug_captured_states is None:
            self.debug_captured_states = []
        logging.info("%s states was captured", len(self.debug_captured_states))
        if len(self.debug_captured_states) < 2:
            return

        gstate1 = self.debug_captured_states[0]
        gstate2 = self.debug_captured_states[1]

        for i, (s1, s2) in enumerate(zip(gstate1.states, gstate2.states)):
            if s1.vg_state and s2.vg_state:
                if s1.vg_state.id == s2.vg_state.id:
                    logging.info("States of rank %s are the same", i)
                    continue
                self._controller.debug_compare(s1.vg_state.id, s2.vg_state.id)

        for gstate in self.debug_captured_states:
            gstate.dispose()
        self.cleanup()

    def cleanup(self):
        self.buffer_manager.cleanup()
        for controller in self.controllers:
            controller.cleanup_states()

    def fast_partial_expand(self, gcontext):
        for state in gcontext.gstate.states:
            if state.status == State.StatusWaitAll or \
                    state.status == State.StatusWaitAny:
                if not state.are_requests_deterministic():
                    continue
                matches = state.check_requests(upto_active=True)
                len(matches) == 1 # Active request are deterministic here

                if not matches[0]:
                    continue

                logging.debug("Fast partial expand pid=%s", state.pid)

                context = gcontext.prepare_context(state.pid)
                context.apply_matching(matches[0])
                return context
        return None

    def fast_expand_node(self, gcontext):
        partial_found = False

        for state in gcontext.gstate.states:
            if state.status == State.StatusWaitAll or \
                    state.status == State.StatusWaitAny or \
                    state.status == State.StatusWaitSome:
                if not state.are_requests_deterministic():
                    continue
                matches = state.check_requests(upto_active=True)
                len(matches) == 1 # Active request are deterministic here

                if not state.is_matching_covering_active_requests(matches[0]):
                   partial_found = True
                   continue

                if state.status == State.StatusWaitAny \
                        or state.status == State.StatusWaitSome:
                    count = len(state.active_request_ids) - \
                                state.active_request_ids.count(consts.MPI_COMM_NULL)
                    if count > 1:
                        # We cannot continue because we need branching,
                        # so the best we can hope
                        # for is "partial_found"
                        continue
                    assert count == 1

                logging.debug("Fast expand status=wait pid=%s", state.pid)
                context = gcontext.prepare_context(state.pid)
                if state.status == State.StatusWaitAny:
                    for i, request_id in enumerate(state.active_request_ids):
                        if request_id != consts.MPI_REQUEST_NULL:
                            context.controller.write_int(state.index_ptr, i)
                            break
                    else:
                        raise Exception("Internal error")

                if state.status == State.StatusWaitSome:
                    for i, request_id in enumerate(state.active_request_ids):
                        if request_id != consts.MPI_REQUEST_NULL:
                            index_ptr, outcounts_ptr = state.index_ptr
                            context.controller.write_int(index_ptr, i)
                            context.controller.write_int(outcounts_ptr, 1)
                            break
                    else:
                        raise Exception("Internal error")

                context.apply_matching(matches[0])
                context.finish_all_active_requests()
                context.run()
                return context

            if state.status == State.StatusReady:
                logging.debug("Fast expand status=init pid=%s", state.pid)
                context = gcontext.prepare_context(state.pid)
                context.run()
                return context

        if partial_found:
            return self.fast_partial_expand(gcontext)
        return None

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
                       eager_threshold, rendezvous_threshold = \
                               gstate.send_protocol_thresholds
                       assert eager_threshold <= rendezvous_threshold
                       if buffered:
                           buffered_size = \
                               max(max(r.message.size for r in buffered),
                                   eager_threshold)
                       else:
                           buffered_size = eager_threshold

                       if synchronous:
                           synchronous_size = \
                               min(min(r.message.size for r in synchronous),
                                   rendezvous_threshold)
                       else:
                           synchronous_size = rendezvous_threshold

                       if buffered_size >= rendezvous_threshold or \
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
                    node.add_arc(Arc(new_node))
                    new_state_created = True
                if new_state_created:
                    return True
        return False

    def expand_node(self, node, gstate):
        logging.debug("--------- Expanding node %s %s ------------", node.uid, gstate)

        if self.debug_compare_states is not None \
                and node.uid in self.debug_compare_states:
            if self.debug_captured_states is None:
                self.debug_captured_states = []
            self.debug_captured_states.append(gstate.copy())

        gcontext = GlobalContext(self, node, gstate)
        fast = False
        while True:
            context = self.fast_expand_node(gcontext)
            if context is None:
                break
            fast = True

        if fast:
            gcontext.make_node()
            return

        if self.fork_standard_sends(node, gstate):
            gstate.dispose()
            return

        for state in gstate.states:
            if state.status == State.StatusWaitAll:
                self.process_wait_or_test_all(node, state, False)
            elif state.status == State.StatusWaitAny:
                self.process_wait_or_test_any(node, state, False)
            elif state.status == State.StatusWaitSome:
                self.process_wait_or_test_some(node, state, False)
            elif state.status == State.StatusTest:
                self.process_wait_or_test_all(node, state, True)
            elif state.status == State.StatusProbe:
                self.process_probe(node, state)
            elif state.status == State.StatusFinished:
                continue
            else:
                raise Exception("Unknown status")

        if not node.arcs:
            if any(state.status != State.StatusFinished
                   for state in gstate.states):
                active_pids = [ state.pid for state in gstate.states
                                if state.status != State.StatusFinished ]
                gcontext = GlobalContext(self, node, gstate)
                message = errormsg.Deadlock(None,
                                            gcontext=gcontext,
                                            active_pids=active_pids)
                self.add_error_message(message)
            else:
                gstate.mpi_leak_check(self, node)
                node.allocations = sum((state.allocations
                                        for state in gstate.states), [])
        gstate.dispose()

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
            context = self.make_copy_and_prepare_context(node, state)
            context.controller.write_int(flag_ptr, 0)
            context.run_and_make_node()
            if status_ptr:
                # TODO: Set status as undefined
                pass

        for message in messages:
            context = self.make_copy_and_prepare_context(node, state)
            if flag_ptr is not None:
                context.controller.write_int(flag_ptr, 1)
            if status_ptr:
                context.controller.write_status(status_ptr,
                                                message.source,
                                                message.tag,
                                                message.size)
            context.state.add_probed_message(comm_id, source, tag, message)
            context.run_and_make_node()

    def make_context(self, node, state):
        # This function exists to avoid importing GlobalContext in state.py
        gcontext = GlobalContext(self, node, state.gstate)
        return gcontext.get_context(state.pid)

    def make_copy_and_prepare_context(self, node, state):
        new_gstate = state.gstate.copy()
        gcontext = GlobalContext(self, node, new_gstate)
        return gcontext.prepare_context(state.pid)

    def process_wait_or_test_all(self, node, state, test):
        if test:
            context = self.make_copy_and_prepare_context(node, state)
            context.controller.write_int(state.flag_ptr, 0)
            context.run_and_make_node()

        matches = state.check_requests()
        logging.debug("Wait or test all: state=%s matches=%s", state, matches)
        for matching in matches:
            covered = state.is_matching_covering_active_requests(matching)
            if not covered and not any(r.is_receive() for r, m in matching):
                # Not all request is completed and no new receive request
                # matched so there is no reason to create new state
                continue
            logging.debug("covered=%s", covered)
            context = self.make_copy_and_prepare_context(node, state)
            context.apply_matching(matching)
            if not covered:
                # Not all active requests are ready, so just apply matchings
                # and create new state
                context.make_node()
                return
            context.state.finish_all_active_requests(context)
            if test:
                context.controller.write_int(state.flag_ptr, 1)
            context.run_and_make_node()

    def process_wait_or_test_any(self, node, state, test):
        assert not test # Test not supported yet
        matches = state.check_requests()
        logging.debug("Wait or test any: state=%s matches=%s", state, matches)
        for matching in matches:
            for i, request in \
                state.active_requests_covered_by_matching(matching):

                logging.debug("Wait any choice: request=%s", request)
                context = self.make_copy_and_prepare_context(node, state)
                context.apply_matching(matching)
                context.controller.write_int(context.state.index_ptr, i)

                # We need to refresh request, from new state
                request = context.state.get_request(request.id)
                context.state.finish_active_request(context, request)
                #if test:
                #    self.controller.write_int(state.flag_ptr, 1)
                context.run_and_make_node()

    def process_wait_or_test_some(self, node, state, test):
        #if test:
        #    new_gstate = state.gstate.copy()
        #    new_state = new_gstate.get_state(state.pid)
        #    new_state.reinit_active_requests()
        #    self.controller.restore_state(new_state.vg_state.id)
        #    self.controller.write_int(state.flag_ptr, 0)
        #    self.execute_state_and_add_node(node, new_state)

        matches = state.check_requests()
        logging.debug("Wait or test any: state=%s matches=%s", state, matches)
        for matching in matches:
            for requests in \
                power_set(state.active_requests_covered_by_matching(matching)):

                if not requests:
                    continue

                logging.debug("Wait some choice: request=%s", requests)
                context = self.make_copy_and_prepare_context(node, state)
                context.apply_matching(matching)
                index_ptr, outcounts_ptr = context.state.index_ptr
                context.controller.write_int(outcounts_ptr, len(requests))
                indices = [ i for i, request in requests ]
                context.controller.write_ints(index_ptr, indices)
                # We need to refresh request, from new state
                context.state.finish_active_requests(context, indices)
                #if test:
                #    self.controller.write_int(state.flag_ptr, 1)
                context.run_and_make_node()

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

        uid = ",".join([ str(state.vg_state.id) if state.vg_state is not None else "F"
                 for state in gstate.states ])
        #uids += [ [ m.vg_buffer.id for m in s.messages ] for s in gstate.states ]

        node = Node(uid, hash)
        logging.debug("New node %s", node.uid)

        if prev:
            node.prev = prev
        self.statespace.add_node(node)
        self.working_queue.append((node, gstate))

        if self.debug_state == uid:
            context = Context(self, node, None)
            context.add_error_and_throw(
                    errormsg.StateCaptured(context, uid=uid))
        return node

    def create_report(self, args):
        for error_message in self.error_messages:
            if error_message.node:
                error_message.events = \
                        self.statespace.events_to_node(error_message.node, None)
                if self.stdout_mode == "capture":
                    error_message.stdout = \
                            [ self.statespace.stream_to_node(
                                error_message.node,
                                None,
                                STREAM_STDOUT,
                                pid)
                              for pid in xrange(self.process_count) ]
                if self.stderr_mode == "capture":
                    error_message.stderr = \
                            [ self.statespace.stream_to_node(
                                error_message.node,
                                None,
                                STREAM_STDERR,
                                pid)
                              for pid in xrange(self.process_count) ]
        return Report(self, args)
