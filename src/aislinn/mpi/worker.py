#
#    Copyright (C) 2015 Stanislav Bohm
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
from base.controller import BufferManager, make_interconnection_pairs
from mpi.controller import Controller
from base.node import Node
from base.utils import power_set
from gcontext import GlobalContext
from globalstate import GlobalState
from collections import deque
from state import State
import consts
import errormsg
import logging


class TransferContext:

    def __init__(self, worker, sockets, target_worker, target_sockets):
        self.worker = worker
        self.sockets = sockets
        self.target_worker = target_worker
        self.target_sockets = target_sockets
        self.translate_table = {}

    def set_translate(self, source, target):
        assert source not in self.translate_table
        self.translate_table[source] = target

    def transfer_state(self, pid, vg_state):
        logging.debug("Transferring state: %s pid: %s", vg_state, pid)
        controller = self.target_worker.controllers[pid]
        state = controller.get_cached_state(vg_state.hash)
        if state is not None:
            state.inc_ref_revive()
            return state
        self.worker.controllers[pid].push_state(self.sockets[pid], vg_state)
        return controller.pull_state(self.target_sockets[pid], vg_state.hash)

    def transfer_buffer(self, vg_buffer):
        logging.debug("Transferring buffer: %s", vg_buffer)
        assert vg_buffer.data is None # Data are already pushed in clients
        controllers = self.worker.controllers
        pids = [ controllers.index(c) for c in vg_buffer.controllers ]
        data = vg_buffer.controllers[0].read_buffer(vg_buffer.id)
        buffer = self.target_worker.buffer_manager.new_buffer(data)
        buffer.remaining_controllers = len(pids)
        for pid in pids:
            self.target_worker.controllers[pid].add_buffer(buffer)
        return buffer


class Worker:

    def __init__(self, worker_id, workers_count, generator, args, valgrind_args, aislinn_args):
        self.generator = generator
        self.worker_id = worker_id
        self.gcontext = None
        self.buffer_manager = BufferManager(10 + worker_id, workers_count)
        self.controllers = [ Controller(args)
                             for i in xrange(generator.process_count) ]
        self.interconnect_sockets = [ None ] * workers_count

        for i, controller in enumerate(self.controllers):
            controller.valgrind_args = valgrind_args
            controller.name = i + worker_id * generator.process_count
            controller.profile = generator.profile

        if aislinn_args.debug_by_valgrind_tool:
            for controller in self.controllers:
                controller.debug_by_valgrind_tool = \
                        aislinn_args.debug_by_valgrind_tool

        if aislinn_args.debug_vglogfile is not None:
            for controller in self.controllers:
                prefix = aislinn_args.debug_vglogfile
                filename = prefix + ".out." + str(controller.name)
                logging.debug(
                        "Openining logfile '%s' for %s", filename, controller)
                controller.stdout_file = open(filename, "w")

                filename = prefix + ".err." + str(controller.name)
                logging.debug(
                        "Openining logfile '%s' for %s", filename, controller)
                controller.stderr_file = open(filename, "w")

        if workers_count > 1:
            # There is a weird bug, that transfering states broke down
            # dynamic resolving of symbols, or at least LD_PRELOAD symbols
            # Hence we force resolve all symbols at runtime
            for controller in self.controllers:
                controller.extra_env = { "LD_BIND_NOW" : "1" }

        self.queue = deque()

    def get_controller(self, pid):
        return self.controllers[pid]

    def start_controllers(self):
        # We do actions separately to allow parallel initialization
        for controller in self.controllers:
            controller.start(capture_syscalls=["write"])

    def connect_controllers(self):
        for controller in self.controllers:
            controller.connect()

    def make_initial_node(self):
        initial_node = Node("init", None)
        self.generator.statespace.add_node(initial_node)
        self.generator.statespace.initial_node = initial_node

        gstate = GlobalState(self.generator.process_count)
        gcontext = GlobalContext(self, initial_node, gstate)

        # TODO: Do it in parallel
        for i in xrange(self.generator.process_count):
            context = gcontext.get_context(i)
            if not context.initial_run():
                return False

        gcontext.make_node()
        gcontext.add_to_queue(None, False)
        return True

    def init_nonfirst_worker(self):
        for controller in self.controllers:
            # Read the first line, it is probably "CALL MPI_Init"
            # or something line this
            # but since we just need an initied process, we don't care
            while True:
                line = controller.receive_line()
                if line.startswith("CALL"):
                    break
                if line.startswith("PROFILE") or line.startswith("EXIT"):
                    continue
                if line.startswith("SYSCALL"):
                    controller.run_drop_syscall_async()
                    continue
                assert 0

    def add_to_queue(self, node, gstate, action):
        self.queue.append((node, gstate, action))

    def start_gcontext(self, node, gstate, action):
        """
        """
        logging.debug("Starting gcontext %s %s %s", self, node, gstate)
        gcontext = GlobalContext(self, node, gstate)
        self.gcontext = gcontext
        if action:
            action.apply_action(gcontext)
            gcontext.action = action
        return self.continue_in_execution()

    def check_collective_requests(self, gcontext):
        for state in gcontext.gstate.states:
            for r in state.active_requests:
                if r.is_collective():
                    if state.gstate.get_operation_by_cc_id(
                            r.comm.comm_id, r.cc_id).can_be_completed(state):
                        state.finish_collective_request(r)
                        return True
        return False

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
               context = gcontext.prepare_context(state.pid)
               context.close_all_requests()
               context.run()
               return True

        if state.status == State.StatusReady:
            logging.debug("Continue ready with flag %s", state)
            gcontext.prepare_context(state.pid).run()
            return True

        if state.status == State.StatusWaitSome and \
           state.waits_for_single_non_null_request() and \
           state.are_tested_requests_finished():
                context = gcontext.prepare_context(state.pid)
                context.continue_waitsome(
                    [ state.index_of_first_non_null_request() ])
                context.run()
                return True

        if state.status == State.StatusWaitAny and \
                state.waits_for_single_non_null_request() and \
                state.are_tested_requests_finished():
                context = gcontext.prepare_context(state.pid)
                context.continue_waitany(
                        state.index_of_first_non_null_request())
                context.run()
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
        return False

    def fast_expand(self):
        gcontext = self.gcontext
        while True:
            matching = gcontext.find_deterministic_match()
            if matching:
                gcontext.apply_matching(matching)
                continue

            if gcontext.gstate.collective_operations \
               and self.check_collective_requests(gcontext):
                   continue

            if self.generator.debug_seq: # DEBUG --debug-seq
                if all(not gcontext.is_pid_running(state.pid)
                       for state in gcontext.gstate.states):
                    for state in gcontext.gstate.states:
                        if self.fast_expand_state(gcontext, state):
                            return True
                    return False
                else:
                    return True

            running = False
            for state in gcontext.gstate.states:
                if not gcontext.is_pid_running(state.pid):
                    running |= self.fast_expand_state(gcontext, state)
                else:
                    running = True

            self.buffer_manager.cleanup()
            return running

    def expand_waitsome(self, gcontext, state, actions):
        indices = state.get_indices_of_tested_and_finished_requests()
        if not indices:
            return
        logging.debug("Expanding waitsome %s", state)
        for indices in power_set(indices):
            if not indices:
                continue # skip empty set
            actions.append(ActionWaitSome(state.pid, indices))

    def expand_testall(self, gcontext, state, actions):
        logging.debug("Expanding testall %s", state)
        actions.append(ActionFlag0(state.pid))
        if state.are_tested_requests_finished():
            actions.append(ActionTestAll(state.pid))

    def expand_waitany(self, gcontext, state, actions):
        logging.debug("Expanding waitany %s", state)
        indices = state.get_indices_of_tested_and_finished_requests()
        if not indices:
            return
        for i in indices:
            actions.append(ActionWaitAny(state.pid, i))

    def expand_probe(self, gcontext, state, actions):
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

    def get_actions(self, gcontext):
        actions = [ ActionMatching(matching)
                    for matching in gcontext.find_nondeterministic_matches() ]
        for state in gcontext.gstate.states:
            if state.status == State.StatusWaitAny:
               self.expand_waitany(gcontext, state, actions)
            elif state.status == State.StatusProbe:
                self.expand_probe(gcontext, state, actions)
            elif state.status == State.StatusWaitSome:
                self.expand_waitsome(gcontext, state, actions)
            elif state.status == State.StatusTest:
                self.expand_testall(gcontext, state, actions)
        return actions

    def slow_expand(self, gcontext):
        actions = self.get_actions(gcontext)
        if actions:
            for i, action in enumerate(actions):
                action.action_index = i
                gcontext.add_to_queue(action, True)
        return bool(actions)

    def continue_in_execution(self):
        if self.fast_expand():
            return True

        gcontext = self.gcontext
        gstate = gcontext.gstate

        # We will plan some computation but leaving this function,
        # current gcontext is finished
        self.gcontext = None

        if not gcontext.make_node():
            gcontext.gstate.dispose() # Node already explored
            return False

        if not self.slow_expand(gcontext):
            node = gcontext.node
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
        return False

        """
        if self.debug_compare_states is not None \
                and node.uid in self.debug_compare_states:
            if self.debug_captured_states is None:
                self.debug_captured_states = []
            self.debug_captured_states.append(gstate.copy())
        """

    def running_controllers(self):
        return [ c for c in self.controllers if c.running ]

    def kill_controllers(self):
        for controller in self.controllers:
            controller.kill()

    def make_context(self, node, state):
        # This function exists to avoid importing GlobalContext in state.py
        gcontext = GlobalContext(self, node, state.gstate)
        return gcontext.get_context(state.pid)

    def cleanup(self):
        self.buffer_manager.cleanup()
        for controller in self.controllers:
            controller.cleanup_states()

    def before_final_check(self):
        for controller in self.controllers:
            controller.make_buffers()
        self.cleanup()

    def final_check(self):
        assert not self.queue

        for controller in self.controllers:
            # Check there is no memory leak
            assert controller.states_count == 0
            stats = controller.get_stats()
            # All pages are active, i.e. we have freed everyhing else
            assert stats["pages"] == stats["active-pages"]
            assert stats["vas"] - 4 <= stats["pages"] # There are 4 predefined VAs
            assert stats["buffers-size"] == 0

        assert self.buffer_manager.resource_count == 0

    def interconnect(self, worker):
        sockets = self.interconnect_sockets[worker.worker_id]
        if sockets is not None:
            return # Already connected
        assert self.worker_id != worker.worker_id
        sockets1, sockets2 = make_interconnection_pairs(
                self.controllers, worker.controllers)
        self.interconnect_sockets[worker.worker_id] = sockets1
        worker.interconnect_sockets[self.worker_id] = sockets2

    def transfer_gstate_and_action(self, worker, gstate, action):
        transfer_context = TransferContext(
                self,
                self.interconnect_sockets[worker.worker_id],
                worker,
                worker.interconnect_sockets[self.worker_id])
        gstate = gstate.transfer(transfer_context)
        if action is not None:
            action = action.transfer(transfer_context)
        return gstate, action

    def start_next_in_queue(self):
        logging.debug("Start_next_in_queue %s", self)

        if not self.queue:
            return

        while True:
            while True:

                if self.generator.search == "dfs":
                    node, gstate, action = self.queue.pop()
                else: # bfs
                    node, gstate, action = self.queue.popleft()

                if not self.queue:
                    break

                worker = self.generator.sleeping_neighbours_of(self.worker_id)

                if worker is None:
                    break

                for controller in self.controllers:
                    controller.make_buffers()

                logging.debug("---- Transfer %s ==> %s ----", self, worker)

                self.interconnect(worker)
                new_gstate, new_action = self.transfer_gstate_and_action(
                        worker, gstate, action)
                gstate.dispose()
                logging.debug("---- End of transfer ----")
                for controller in worker.controllers:
                    controller.make_buffers()
                if not worker.start_gcontext(node, new_gstate, new_action):
                    worker.start_next_in_queue()
            if self.start_gcontext(node, gstate, action):
                break

    def __repr__(self):
        return "<Worker {0} queue={1}>".format(self.worker_id, len(self.queue))
