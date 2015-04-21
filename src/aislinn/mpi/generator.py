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
#    along with Aislinn.  If not, see <http://www.gnu.org/licenses/>.
#


from base.controller import BufferManager, poll_controllers
from base.node import Node, Arc
from base.report import Report
from base.statespace import StateSpace
from base.stream import STREAM_STDOUT, STREAM_STDERR
from base.utils import power_set
from collections import deque
from gcontext import GlobalContext, ErrorFound
from globalstate import GlobalState
from mpi.context import Context
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
        self.debug_seq = aislinn_args.debug_seq

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
        pages = 0
        active_pages = 0
        buffers_size = 0
        for controller in self.controllers:
            stats = controller.get_stats()
            pages += stats["pages"]
            active_pages = stats["active-pages"]
            buffers_size = stats["buffers-size"]
        self.statistics.append((
            len(self.working_queue), pages, active_pages, buffers_size))

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
        logging.info("Hashes %s, %s", gstate1.compute_hash(), gstate2.compute_hash())
        for i, (s1, s2) in enumerate(zip(gstate1.states, gstate2.states)):
            if s1.vg_state and s2.vg_state:
                logging.info("Pids %s %s %s", i, s1.vg_state.hash, s2.vg_state.hash)
                if s1.vg_state.id == s2.vg_state.id:
                    logging.info("States of rank %s are the same", i)
                else:
                    self._controller.debug_compare(s1.vg_state.id, s2.vg_state.id)
                for name in s1.__dict__.keys():
                    if getattr(s1, name) != getattr(s2, name):
                        logging.info("stateA: %s %s", name, getattr(s1, name))
                        logging.info("stateB: %s %s", name, getattr(s2, name))

        for gstate in self.debug_captured_states:
            gstate.dispose()
        self.cleanup()

    def cleanup(self):
        self.buffer_manager.cleanup()
        for controller in self.controllers:
            controller.cleanup_states()

    def check_collective_requests(self, gcontext):
        for state in gcontext.gstate.states:
            for r in state.active_requests:
                if r.is_collective():
                    if state.gstate.get_operation_by_cc_id(
                            r.comm.comm_id, r.cc_id).can_be_completed(state):
                        state.finish_collective_request(r)
                        return True
        return False

    def continue_waitany(self, gcontext, state):
        logging.debug("Continue waitsome %s", state)
        context = gcontext.prepare_context(state.pid)
        context.controller.write_int(context.state.index_ptr, state.select)
        context.close_requests((state.select,))
        context.run()

    def continue_waitsome(self, gcontext, state):
        logging.debug("Continue waitsome %s", state)
        context = gcontext.prepare_context(state.pid)
        index_ptr, outcounts_ptr = context.state.index_ptr
        indices = state.select
        context.controller.write_int(outcounts_ptr, len(indices))
        context.controller.write_ints(index_ptr, indices)
        context.close_requests(indices)
        context.run()

    def continue_ready(self, gcontext, state):
        logging.debug("Continue ready with flag %s", state)
        context = gcontext.prepare_context(state.pid)
        if state.flag_ptr:
            context.controller.write_int(state.flag_ptr, 0)
        context.run()

    def continue_waitall(self, gcontext, state):
        logging.debug("Continue waitall %s", state)
        context = gcontext.prepare_context(state.pid)
        context.close_all_requests()
        context.run()

    def continue_testall(self, gcontext, state):
        logging.debug("Continue testall %s", state)
        context = gcontext.prepare_context(state.pid)
        context.controller.write_int(state.flag_ptr, 1)
        context.close_all_requests()
        context.run()

    def continue_probe(self, gcontext, state, rank):
        logging.debug("Continue probe %s", state)
        comm_id, source, tag, status_ptr = state.probe_data
        pid, request = state.probe_deterministic(comm_id, rank, tag)
        context = gcontext.prepare_context(state.pid)
        if state.flag_ptr:
            context.controller.write_int(state.flag_ptr, 1)
        context.controller.write_status(
                status_ptr, rank, request.tag, request.vg_buffer.size)
        context.run()

    def fast_expand_state(self, gcontext, state):
        if (state.status == State.StatusWaitAll
            and state.are_tested_requests_finished()):
               self.continue_waitall(gcontext, state)
               return True

        if state.status == State.StatusReady:
            self.continue_ready(gcontext, state)
            return True

        if state.status == State.StatusWaitSome:
            if state.select is not None:
                self.continue_waitsome(gcontext, state)
                return True
            elif state.waits_for_single_non_null_request() and \
                state.are_tested_requests_finished():
                state.select = [ state.index_of_first_non_null_request() ]
                self.continue_waitsome(gcontext, state)
                return True

        if state.status == State.StatusWaitAny:
            if state.select is not None:
                self.continue_waitany(gcontext, state)
                return True
            elif state.waits_for_single_non_null_request() and \
                state.are_tested_requests_finished():
                state.select = state.index_of_first_non_null_request()
                self.continue_waitany(gcontext, state)
                return True

        if state.status == State.StatusProbe:
            comm_id, source, tag, status_ptr = state.probe_data
            rank = state.get_probe_promise(comm_id, source, tag)
            if rank is not None:
                self.continue_probe(gcontext, state, rank)
                return True
            elif state.probe_data[1] != consts.MPI_ANY_SOURCE and state.flag_ptr is None:
                probed = state.probe_deterministic(comm_id, source, tag)
                if probed:
                    pid, request = probed
                    rank = request.comm.group.pid_to_rank(pid)
                    self.continue_probe(gcontext, state, rank)
                    return True

        if state.status == State.StatusTest and state.select:
            self.continue_testall(gcontext, state)
            return True
        return False

    def poll_controllers(self, gcontext):
        controllers = [ c for c in self.controllers if c.running ]
        logging.debug("Running controllers %s", controllers)
        if not controllers:
            return False
        controllers = poll_controllers(controllers)
        for c in controllers:
            context = gcontext.get_context(c.name)
            logging.debug("Ready controller %s", context)
            result = c.finish_async()
            context.process_run_result(result)
        return True

    def fast_expand_node(self, gcontext):
        modified = False
        while True:
            matching = gcontext.find_deterministic_match()
            if matching:
                gcontext.apply_matching(matching)
                modified = True
                continue

            if gcontext.gstate.collective_operations \
               and self.check_collective_requests(gcontext):
                   modified = True
                   continue

            if self.debug_seq: # DEBUG --debug-seq
                if all(not gcontext.is_running(state.pid)
                       for state in gcontext.gstate.states):
                    for state in gcontext.gstate.states:
                        if self.fast_expand_state(gcontext, state):
                            break
            else: # Normal run
                for state in gcontext.gstate.states:
                    if not gcontext.is_running(state.pid):
                        self.fast_expand_state(gcontext, state)

            self.buffer_manager.cleanup()
            if self.poll_controllers(gcontext):
                modified = True
                continue
            return modified

    def fork_standard_sends(self, node, gstate):
        new_state_created = False
        for state in gstate.states:
            if state.status == State.StatusWaitAll or \
                    state.status == State.StatusTest or \
                    state.status == State.StatusWaitAny:
                requests = state.fork_standard_sends()
                if requests is None:
                    continue
                logging.debug("Forking because of standard send %s", requests)
                for buffered, synchronous in requests:
                    if self.send_protocol == "dynamic":
                       eager_threshold, rendezvous_threshold = \
                               gstate.send_protocol_thresholds
                       assert eager_threshold <= rendezvous_threshold
                       if buffered:
                           buffered_size = \
                               max(max(r.vg_buffer.size for r in buffered),
                                   eager_threshold)
                       else:
                           buffered_size = eager_threshold

                       if synchronous:
                           synchronous_size = \
                               min(min(r.vg_buffer.size for r in synchronous),
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
                        new_state.set_request_as_buffered(r)
                    for r in synchronous:
                        new_state.set_request_as_synchronous(r)
                    new_node = self.add_node(node, new_gstate)
                    node.add_arc(Arc(new_node))
                    new_state_created = True
                if new_state_created:
                    return True
        return False

    def setup_select_and_make_node(self, gcontext, state, select):
        gstate = gcontext.gstate.copy()
        gstate.states[state.pid].select = select
        g = GlobalContext(self, gcontext.node, gstate)
        g.make_node()

    def set_flag0_and_make_node(self, gcontext, state):
        gstate = gcontext.gstate.copy()
        gstate.states[state.pid].set_ready_flag0()
        g = GlobalContext(self, gcontext.node, gstate)
        g.make_node()

    def set_probe_promise_and_make_node(
            self, gcontext, state, comm_id, source, t, rank):
        gstate = gcontext.gstate.copy()
        state = gstate.states[state.pid]
        state.set_probe_promise(comm_id, source, t, rank)
        g = GlobalContext(self, gcontext.node, gstate)
        g.make_node()

    def expand_waitsome(self, gcontext, state):
        logging.debug("Expanding waitsome %s", state)
        indices = state.get_indices_of_tested_and_finished_requests()
        if not indices:
            return
        for indices in power_set(indices):
            if not indices:
                continue # skip empty set
            self.setup_select_and_make_node(gcontext, state, indices)

    def expand_testall(self, gcontext, state):
        logging.debug("Expanding testall %s", state)
        self.set_flag0_and_make_node(gcontext, state)
        if state.are_tested_requests_finished():
            self.setup_select_and_make_node(gcontext, state, True)

    def expand_waitany(self, gcontext, state):
        logging.debug("Expanding waitany %s", state)
        indices = state.get_indices_of_tested_and_finished_requests()
        if not indices:
            return
        for i in indices:
            self.setup_select_and_make_node(gcontext, state, i)

    def expand_probe(self, gcontext, state):
        logging.debug("Expanding probe %s", state)
        comm_id, source, tag, status_ptr = state.probe_data
        if state.get_probe_promise(comm_id, source, tag) is not None:
            return

        if state.flag_ptr:
            self.set_flag0_and_make_node(gcontext, state)
            if source != consts.MPI_ANY_SOURCE:
                 probed = state.probe_deterministic(comm_id, source, tag)
                 if probed:
                     pid, request = probed
                     rank = request.comm.group.pid_to_rank(pid)
                     self.set_probe_promise_and_make_node(
                          gcontext, state, comm_id, source, tag, rank)
        if source != consts.MPI_ANY_SOURCE:
            return
        for pid, request in state.probe_nondeterministic(comm_id, tag):
            rank = request.comm.group.pid_to_rank(pid)
            self.set_probe_promise_and_make_node(
                    gcontext, state, comm_id, source, tag, rank)

    def slow_expand(self, gcontext):
        for matching in gcontext.find_nondeterministic_matches():
            logging.debug("Slow expand matching = %s", matching)
            g = GlobalContext(self, gcontext.node, gcontext.gstate.copy())
            g.apply_matching(matching)
            g.make_node()

        for state in gcontext.gstate.states:
            if state.status == State.StatusWaitAny:
                self.expand_waitany(gcontext, state)
            elif state.status == State.StatusWaitSome:
                self.expand_waitsome(gcontext, state)
            elif state.status == State.StatusProbe:
                self.expand_probe(gcontext, state)
            elif state.status == State.StatusTest:
                self.expand_testall(gcontext, state)

    def expand_node(self, node, gstate):
        logging.debug("--------- Expanding node %s %s ------------", node.uid, gstate)

        if self.debug_compare_states is not None \
                and node.uid in self.debug_compare_states:
            if self.debug_captured_states is None:
                self.debug_captured_states = []
            self.debug_captured_states.append(gstate.copy())

        gcontext = GlobalContext(self, node, gstate)

        if self.fast_expand_node(gcontext):
            gcontext.make_node()
            return

        if self.fork_standard_sends(node, gstate):
            gstate.dispose()
            return

        self.slow_expand(gcontext)

        if not node.arcs:
            if any(state.status != State.StatusFinished
                   for state in gstate.states):
                active_pids = [ state.pid for state in gstate.states
                                if state.status != State.StatusFinished ]
                gcontext = GlobalContext(self, node, gstate)
                message = errormsg.Deadlock(None,
                                            gcontext=gcontext,
                                            active_pids=active_pids)
                gcontext.add_error_and_throw(message)
            else:
                gstate.mpi_leak_check(self, node)
                node.allocations = sum((state.allocations
                                        for state in gstate.states), [])
        gstate.dispose()

    def make_context(self, node, state):
        # This function exists to avoid importing GlobalContext in state.py
        gcontext = GlobalContext(self, node, state.gstate)
        return gcontext.get_context(state.pid)

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
        """
        uid = []
        for state in gstate.states:
            if state.vg_state is not None:
                u = str(state.vg_state.id)
            else:
                u = "F"
            if state.select is not None:
                u += "s"
            uid.append(u)

        uid = ",".join(uid)
        """
        uid = str(self.statespace.nodes_count)
        #uid = ",".join([ str(state.vg_state.id) if state.vg_state is not None else "F"
        #         for state in gstate.states ])
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
