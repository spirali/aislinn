#
#    Copyright (C) 2015, 2016 Stanislav Bohm
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
import base.utils as utils
from gcontext import GlobalContext
from globalstate import GlobalState
from collections import deque
from state import State
from vgtool.controller import BufferManager, make_interconnection_pairs
from vgtool.controller import poll_controllers
import base.paths
import consts
import errormsg
import msgpack
from vgtool.socketwrapper import SocketWrapper


import logging
import socket
from datetime import datetime

try:
    import cPickle as pickle
except:
    import pickle


class Worker:

    def __init__(self, addr, port):
        s = socket.create_connection((addr, port))
        self.socket = SocketWrapper(s)
        self.socket.set_no_delay()
        worker_id, size = map(int, self.socket.read_line().split())
        self.worker_id = worker_id

        data = self.socket.read_data(size)
        args, run_args = pickle.loads(data)

        process_count = args.p
        workers_count = args.workers

        self.process_count = process_count
        self.gcontext = None
        self.current_state = None
        self.consts_pool = None
        self.buffer_manager = BufferManager(10 + worker_id, workers_count)

        self.send_protocol = args.send_protocol
        self.send_protocol_eager_threshold = \
            args.send_protocol_eager_threshold
        self.send_protocol_rendezvous_threshold = \
            args.send_protocol_rendezvous_threshold
        self.message_sizes = set()

        self.controllers = [Controller(base.paths.VALGRIND_BIN, run_args)
                            for i in xrange(process_count)]
        self.worker_sockets = [None] * workers_count
        self.controller_sockets = [None] * workers_count

        self.stdout_mode = args.stdout
        self.stderr_mode = args.stderr

        for i, controller in enumerate(self.controllers):
            controller.name = i + worker_id * process_count
            controller.profile = args.profile

            if args.vgv:
                controller.verbose = args.vgv

            if args.heap_size is not None:
                controller.heap_size = args.heap_size

            if args.redzone_size is not None:
                controller.redzone_size = args.redzone_size

            if args.debug_by_valgrind_tool:
                controller.debug_by_valgrind_tool = \
                    args.debug_by_valgrind_tool

            if args.debug_vglogfile is not None:
                prefix = args.debug_vglogfile
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

        if args.debug_stats:
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
        self.make_state()
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

        self.process_commands()
        self.kill_controllers()

    def listen(self, worker_id):
        s, port = utils.start_listen(0, 1)
        try:
            ports = [c.interconn_listen() for c in self.controllers]
            ports.append(port)
            # Send ports
            self.socket.send_data("{}\n".format(" ".join(map(str, ports))))
            s2, addr = s.accept()
            self.worker_sockets[worker_id] = SocketWrapper(s2)
            self.controller_sockets[worker_id] = \
                [c.interconn_listen_finish() for c in self.controllers]
        finally:
            s.close()

    def command_connect(self, command):
        worker_id = int(command[1])
        ports = map(int, command[2:-1])
        port = int(command[-1])
        assert len(self.controllers) == len(ports)
        logging.debug("Connection to worker %s", worker_id)

        self.worker_sockets[worker_id] = \
            SocketWrapper(socket.create_connection(("127.0.0.1", port)))
        for port, c in zip(ports, self.controllers):
            host = "127.0.0.1:{0}".format(port)
            c.interconn_connect(host)
        self.controller_sockets[worker_id] = \
            [c.interconn_connect_finish() for c in self.controllers]

    def push_gstate(self, worker_id, gstate):
        for controller in self.controllers:
            controller.make_buffers()
        buffers = list(set(gstate.get_buffers()))
        buffer_data = []
        first_id = self.controllers[0].name
        for b in buffers:
            controller_ids = [c.name - first_id for c in b.controllers]
            buffer_data.append((b.hash, b.size, controller_ids))
        gstate_data = gstate.serialize_to_list()
        data = msgpack.dumps((buffer_data, gstate_data))
        socket = self.worker_sockets[worker_id]
        socket.send_data("{}\n{}".format(len(data), data))
        sockets = self.controller_sockets[worker_id]
        for controller, s, state in zip(self.controllers,
                                        sockets,
                                        gstate.states):
            if state.vg_state:
                controller.push_state(s, state.vg_state)

        for b in buffers:
            for controller in b.controllers:
                controller.push_buffer(sockets[c.name - first_id], b.id)



    def pull_gstate(self, worker_id):
        socket = self.worker_sockets[worker_id]
        size = int(socket.read_line())
        buffer_data, gstate_data = msgpack.loads(socket.read_data(size))

        # Hack, this can be fix when we separate
        # vg_state and hash
        state_hashes = [gstate_data[i][1] for i in xrange(self.process_count)]
        objects = {}
        sockets = self.controller_sockets[worker_id]

        for controller, s, hash in zip(self.controllers, sockets, state_hashes):
            if hash is not None:
                logging.debug("Pulling state %s", hash)
                objects[hash] = controller.pull_state(s, hash)
        buffers = []
        for hash, size, controller_ids in buffer_data:
            assert controller_ids
            b = self.buffer_manager.new_buffer()
            buffers.append(b)
            controllers = [self.controllers[i] for i in controller_ids]
            for controller in controllers:
                controller.pull_buffer(sockets[i], b.id)
            b.hash = hash
            b.size = size
            b.controllers = controllers
            objects[hash] = b

        gstate = GlobalState(self.process_count, gstate_data, objects)
        for b in buffers:
            b.dec_ref()
        return gstate

    def dispose_current(self):
        if self.current_state:
            self.current_state[1].dispose()
            self.current_state = None
            self.cleanup()

    def process_commands(self):
        while True:
            command = self.socket.read_line().split()
            logging.debug("Received command: %s", command)
            name = command[0]
            if name == "SAVE":
                hash, gstate, actions = self.current_state
                self.gstates[hash] = (gstate, actions)
                self.current_state = None
            elif name == "START":
                self.dispose_current()
                gstate, actions = self.gstates[command[1]]
                action = actions[int(command[2])]
                gstate = gstate.copy()
                self.start_execution(gstate, action)
                self.make_state()
            elif name == "FREE":
                gstate, actions = self.gstates.pop(command[1])
                gstate.dispose()
                self.cleanup()
            elif name == "PUSH":
                worker_id = int(command[1])
                gstate = self.gstates[command[2]][0]
                self.push_gstate(worker_id, gstate)
            elif name == "PULL":
                self.dispose_current()
                self.cleanup()
                gstate = self.pull_gstate(int(command[1]))
                self.gstates[command[2]] = (gstate, gstate.get_actions(self))
            elif name == "LISTEN":
                worker_id = int(command[1])
                logging.debug("Listening for connection from worker %s", worker_id)
                assert worker_id != self.worker_id
                self.listen(worker_id)
            elif name == "CONNECT":
                self.command_connect(command)
            elif name == "FINAL_CHECK":
                if self.current_state:
                    self.current_state[1].dispose()
                    self.current_state = None
                self.final_check()
                return
            elif name == "QUIT":
                return
            else:
                raise Exception("Unknown command:" + name)

    def start_execution(self, gstate, action):
        logging.debug("Starting gcontext %s %s", self, gstate)
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

    def make_state(self):
        # !!! TODO:
        # First hash, then check if save is necessary then save
        self.gcontext.save_states()
        gstate = self.gcontext.gstate
        hash = self.gcontext.gstate.compute_hash()
        actions = gstate.get_actions(self)
        self.new_state(hash, len(actions))
        self.current_state = (hash, gstate, actions)
        self.gcontext = None

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

    def final_check(self):
        for controller in self.controllers:
            controller.make_buffers()
        self.cleanup()

        assert len(self.gstates) == 0

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

    """
    def interconnect(self, worker):
        sockets = self.controller_sockets[worker.worker_id]
        assert sockets is not None
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
    """

    def new_state(self, hash, n_actions):
        self.socket.send_data("STATE {} {}\n".format(hash, n_actions))

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

    def send_error_message(self, error_message):
        data = pickle.dumps(error_message)
        self.socket.send_data("ERROR {}\n{}".format(len(data), data))

    def get_const_ptr(self, id):
        if id == consts.MPI_TAG_UB:
            return self.consts_pool
        raise Exception("Invalid const id")

    def __repr__(self):
        return "<Worker {0} queue={1}>".format(self.worker_id, len(self.queue))
