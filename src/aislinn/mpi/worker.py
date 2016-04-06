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
from mpi.controller import Controller
from base.node import Node
from gcontext import GlobalContext
from globalstate import GlobalState
from collections import deque
from state import State
from vgtool.controller import BufferManager, make_interconnection_pairs
from vgtool.controller import poll_controllers
import base.paths
import consts
import errormsg
import logging
from datetime import datetime



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
        assert vg_buffer.data is None  # Data are already pushed in clients
        controllers = self.worker.controllers
        pids = [controllers.index(c) for c in vg_buffer.controllers]
        data = vg_buffer.controllers[0].read_buffer(vg_buffer.id)
        buffer = self.target_worker.buffer_manager.new_buffer(data)
        buffer.remaining_controllers = len(pids)
        for pid in pids:
            self.target_worker.controllers[pid].add_buffer(buffer)
        return buffer


class Worker:

    def __init__(self, worker_id, workers_count,
                 generator, args, aislinn_args, process_count):
        self.generator = generator
        self.worker_id = worker_id
        self.process_count = process_count
        self.gcontext = None
        self.consts_pool = None
        self.buffer_manager = BufferManager(10 + worker_id, workers_count)

        self.send_protocol = aislinn_args.send_protocol
        self.send_protocol_eager_threshold = \
            aislinn_args.send_protocol_eager_threshold
        self.send_protocol_rendezvous_threshold = \
            aislinn_args.send_protocol_rendezvous_threshold
        self.message_sizes = set()

        self.controllers = [Controller(base.paths.VALGRIND_BIN, args)
                            for i in xrange(process_count)]
        self.interconnect_sockets = [None] * workers_count

        for i, controller in enumerate(self.controllers):
            controller.name = i + worker_id * process_count
            controller.profile = aislinn_args.profile

            if aislinn_args.vgv:
                controller.verbose = aislinn_args.vgv

            if aislinn_args.heap_size is not None:
                controller.heap_size = aislinn_args.heap_size

            if aislinn_args.redzone_size is not None:
                controller.redzone_size = aislinn_args.redzone_size

            if aislinn_args.debug_by_valgrind_tool:
                controller.debug_by_valgrind_tool = \
                    aislinn_args.debug_by_valgrind_tool

            if aislinn_args.debug_vglogfile is not None:
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
                controller.extra_env = {"LD_BIND_NOW": "1"}

        self.queue = deque()
        self.gstates = {}

        if aislinn_args.debug_stats:
            self.stats_time = []
            self.stats_queue_len = []
            self.stats_controller_start = [[] for c in self.controllers]
            self.stats_controller_stop = [[] for c in self.controllers]
        else:
            self.stats_time = None

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
        """
        initial_node = Node("init", None)
        self.generator.statespace.add_node(initial_node)
        self.generator.statespace.initial_node = initial_node
        """

        gstate = GlobalState(self.process_count)
        gcontext = GlobalContext(self, gstate)

        # TODO: Do it in parallel
        for i in xrange(self.process_count):
            context = gcontext.get_context(i)
            if not context.initial_run():
                return False

        self.gcontext = gcontext
        self.execution_main()
        self.make_state(True)
        return True

        """
        gcontext.save_states()
        hash = gstate.compute_hash()

        self.generator.new_state(hash, True)
        self.queue.append(gcontext.gstate)
        line = self.generator.read_line()
        assert line == "NEW"
        return True
        """

    def init_nonfirst_worker(self):
        gstate = GlobalState(self.process_count)
        gcontext = GlobalContext(self, gstate)
        # TODO: Do it in parallel
        for i in xrange(self.process_count):
            context = gcontext.get_context(i)
            if not context.initial_run(False):
                return False
        return True

    def run(self):
        if self.worker_id == 0:
            result = self.make_initial_node()
        else:
            result = self.init_nonfirst_worker()
        if not result:
            raise Exception("Init failed")

        while True:
            if self.queue:
                gstate = self.queue.popleft()
                self.process_state(gstate)
                self.process_command()
            else:
                break

    def process_command(self):
        line = self.generator.read_line()
        print line

    def process_state(self, gstate):
        actions = gstate.get_actions(self)
        if not actions:
            self.generator.socket.send_data("FINAL\n")
            return
        for action in actions:
            last = action == actions[-1]
            if last:
                gs = gstate
            else:
                gs = gstate.copy()
            self.start_execution(gs, action)
            self.make_state(last)

    def start_execution(self, gstate, action):
        logging.debug("Starting gcontext %s %s %s", self, gstate)
        gcontext = GlobalContext(self, gstate)
        self.gcontext = gcontext
        if action:
            action.apply_action(gcontext)
            gcontext.action = action
        self.execution_main()

    def execution_main(self):
        while True:
            self.fast_expand()
            controllers = self.running_controllers()
            if not controllers:
                break
            controllers = poll_controllers(controllers)
            for c in controllers:
                context = self.gcontext.get_context(
                    c.name % self.process_count)
                logging.debug("Ready controller %s", context)
                context.process_run_result(c.finish_async())

    def make_state(self, last):
        gstate = self.gcontext.gstate
        hash = self.gcontext.gstate.compute_hash()
        self.generator.new_state(hash, last)
        line = self.generator.read_line()
        if line == "SAVE":
            self.gcontext.save_states()
            self.gstates[hash] = gstate
            self.queue.append(gstate)
        else:
            assert line == "DROP"

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
        if (state.status == State.StatusWaitAll and
                state.are_tested_requests_finished()):
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
                    [state.index_of_first_non_null_request()])
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
            elif state.probe_data[1] != consts.MPI_ANY_SOURCE and \
                    state.flag_ptr is None:
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

            """
            if self.generator.debug_seq:  # DEBUG --debug-seq
                if all(not gcontext.is_pid_running(state.pid)
                       for state in gcontext.gstate.states):
                    for state in gcontext.gstate.states:
                        if self.fast_expand_state(gcontext, state):
                            return True
                    return False
                else:
                    return True
            """

            for state in gcontext.gstate.states:
                if not gcontext.is_pid_running(state.pid):
                    self.fast_expand_state(gcontext, state)
            self.buffer_manager.cleanup()
            return

    """
    def slow_expand(self, gcontext):
        actions = self.get_actions(gcontext)
        if actions:
            for i, action in enumerate(actions):
                action.action_index = i
                gcontext.add_to_queue(action, True)
        return bool(actions)
    """

    def continue_in_execution(self):
        running = self.fast_expand()
        if running:
            return running

        gcontext = self.gcontext
        gstate = gcontext.gstate

        # We will plan some computation but leaving this function,
        # current gcontext is finished
        self.gcontext = None

        if not gcontext.make_node():
            gcontext.gstate.dispose()  # Node already explored
            return None

        if not self.slow_expand(gcontext):
            node = gcontext.node
            if any(state.status != State.StatusFinished
                   for state in gstate.states):
                active_pids = [state.pid for state in gstate.states
                               if state.status != State.StatusFinished]
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
        return None

        """
        if self.debug_compare_states is not None \
                and node.uid in self.debug_compare_states:
            if self.debug_captured_states is None:
                self.debug_captured_states = []
            self.debug_captured_states.append(gstate.copy())
        """

    def running_controllers(self):
        return [c for c in self.controllers if c.running]

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
            # There are 4 predefined VAs
            assert stats["vas"] - 4 <= stats["pages"]
            assert stats["buffers-size"] == 0

        assert self.buffer_manager.resource_count == 0

    def interconnect(self, worker):
        sockets = self.interconnect_sockets[worker.worker_id]
        if sockets is not None:
            return  # Already connected
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

    def record_process_start(self, controller_id):
        time = datetime.now() - self.generator.init_time
        self.stats_controller_start[controller_id].append(time.total_seconds())

    def record_process_stop(self, controller_id):
        time = datetime.now() - self.generator.init_time
        self.stats_controller_stop[controller_id].append(time.total_seconds())

    def start_next_in_queue(self):
        logging.debug("Start_next_in_queue %s", self)

        if self.stats_time is not None:
            self.record_stats()

        if not self.queue:
            return

        while True:
            while True:

                if self.generator.search == "dfs":
                    node, gstate, action = self.queue.pop()
                else:  # bfs
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

    def record_stats(self):
        time = datetime.now() - self.generator.init_time
        self.stats_time.append(time.total_seconds())
        self.stats_queue_len.append(len(self.queue))

    def get_const_ptr(self, id):
        if id == consts.MPI_TAG_UB:
            return self.consts_pool
        raise Exception("Invalid const id")

    def __repr__(self):
        return "<Worker {0} queue={1}>".format(self.worker_id, len(self.queue))
