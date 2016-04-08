#
#    Copyright (C) 2014, 2015 Stanislav Bohm
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


from base.arc import STREAM_STDOUT, STREAM_STDERR
from base.report import Report
from base.statespace import StateSpace
import base.utils as utils
from context import Context
from gcontext import GlobalContext, ErrorFound
from mpi.ndsync import NdsyncChecker
from base.node import Node
from worker import Worker
from vgtool.controller import poll_controllers
from vgtool.socketwrapper import SocketWrapper

import consts
import errormsg
import logging
import datetime
import socket
import os
import sys
import select
from collections import deque


class Generator:

    def __init__(self, args, process_count, aislinn_args):
        self.args = args
        self.statespace = StateSpace()
        self.process_count = process_count
        self.error_messages = []

        self.init_time = None
        self.end_time = None
        self.deterministic_unallocated_memory = None

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

        self.debug_seq = aislinn_args.debug_seq
        self.debug_arc_times = aislinn_args.debug_arc_times

        self.workers = None
        self.aislinn_args = aislinn_args

    def get_statistics(self):
        return None # DEBUG

        if self.workers[0].stats_time is None:
            return None
        charts = []

        chart = {"type" : "plot",
                 "name" : "Queue lengthts",
                 "data" : []}
        for i, worker in enumerate(self.workers):
            data = (worker.stats_time,
                    worker.stats_queue_len,
                    "Worker {}".format(i))
            chart["data"].append(data)
        charts.append(chart)

        chart = {"type" : "timeline",
                 "name" : "Controllers utilization",
                 "data" : []}
        for i, worker in enumerate(self.workers):
            for j in xrange(self.process_count):
                data = (worker.stats_controller_start[j],
                        worker.stats_controller_stop[j],
                        "Controller {}".format(j))
                assert len(data[0]) == len(data[1])
                chart["data"].append(data)
        charts.append(chart)

        chart = {"type" : "boxplot",
                 "name" : "Controllers utilization",
                 "data" : []}
        for i, worker in enumerate(self.workers):
            for j in xrange(self.process_count):
                starts = worker.stats_controller_start[j]
                stops = worker.stats_controller_stop[j]
                times = []
                for start, stop in zip(starts, stops):
                    times.append(stop - start)
                chart["data"].append(times)
        charts.append(chart)
        chart = {"type" : "bars",
                 "name" : "Controllers utilization",
                 "data" : [sum(d) for d in chart["data"]]}
        charts.append(chart)
        return charts

    def add_error_message(self, error_message):
        if error_message.name in [e.name for e in self.error_messages]:
            return
        self.error_messages.append(error_message)

    def sanity_check(self):
        for node, gstate in self.queue:
            gstate.sanity_check()

    def sleeping_neighbours_of(self, worker_id):
        for i in xrange(1, len(self.workers)):
            worker = self.workers[(i + worker_id) % len(self.workers)]
            if not worker.queue and not worker.gcontext:
                return worker
        return None

    def add_node(self, parent, hash):
        node = self.statespace.get_node_by_hash(hash)
        if node is not None:
            return node, False

        if self.statespace.nodes_count > self.max_states:
            logging.info("Maximal number of states reached")
            if self.debug_compare_states is not None:
                self.debug_compare()
            raise ErrorFound()

        uid = str(self.statespace.nodes_count)
        node = Node(uid, hash)
        self.statespace.add_node(node)

        return node, True

    def start_workers(self):
        s, port = utils.start_listen(0, self.aislinn_args.workers)

        """
        self.workers = [Worker(i,
                               aislinn_args.workers,
                               self,
                               args,
                               aislinn_args)
                        for i in xrange(aislinn_args.workers)]
        """
        workers = []
        for i in xrange(self.aislinn_args.workers):
            pid = os.fork()
            if pid != 0:
                s.close()
                connection = GeneratorConnection(port)
                worker = Worker(connection.read_worker_id(),
                                self.aislinn_args.workers,
                                connection,
                                self.args,
                                self.aislinn_args,
                                self.process_count)
                worker.start_controllers()
                worker.connect_controllers()
                worker.run()
                sys.exit(0)

        workers = [WorkerDescriptor(self, s, i)
                   for i in xrange(self.aislinn_args.workers)]
        initial_node = Node("init", None)
        self.statespace.add_node(initial_node)
        self.statespace.initial_node = initial_node
        workers[0].active_node = initial_node
        self.workers = workers

        """line = workers[0].read_line().split()
        assert line[0] == "STATE"
        node = self.add_node(initial_node, line[1])"""


        """
        for worker in self.workers:
            worker.start_controllers()

        for worker in self.workers:
            worker.connect_controllers()

        if not self.workers[0].make_initial_node():
            return False

        for worker in self.workers[1:]:
            if not worker.init_nonfirst_worker():
                return False

        self.workers[0].start_next_in_queue()
        """
        return True

    def main_cycle(self):

        while True:
            workers = [ worker for worker in self.workers
                        if worker.active_node ]
            if not workers:
                return
            workers = poll_workers(workers)
            for worker in workers:
                worker.process_command()

        """
        while True:
            controllers = sum((worker.running_controllers()
                               for worker in self.workers if worker.gcontext),
                              [])
            logging.debug("Running controllers %s", controllers)
            if not controllers:
                return
            controllers = poll_controllers(controllers)
            for c in controllers:
                worker = self.workers[c.name / self.process_count]
                #if worker.stats_time is not None:
                #    worker.record_process_stop(c.name % self.process_count)
                context = worker.gcontext.get_context(
                    c.name % self.process_count)
                logging.debug("Ready controller %s", context)
                context.process_run_result(c.finish_async())
                worker.continue_in_execution()
                if worker.gcontext is None:
                    worker.start_next_in_queue()
        """

    def run(self):
        self.init_time = datetime.datetime.now()
        try:
            if not self.start_workers():
                return False

            self.main_cycle()
            for worker in self.workers:
                worker.send_command("QUIT\n")
            """
            self.memory_leak_check()
            self.final_check()
            if self.send_protocol == "full" and not self.error_messages:
                self.ndsync_check()
            """
            self.is_full_statespace = True

        except ErrorFound:
            logging.debug("ErrorFound catched")
        finally:
            #for worker in self.workers:
            #    worker.kill_controllers()
            self.end_time = datetime.datetime.now()
        return True

    def ndsync_check(self):
        self.statespace.inject_dfs_indegree()
        message = NdsyncChecker(self, self.statespace).run()
        if message:
            self.add_error_message(message)

    def memory_leak_check(self):
        final_nodes = list(self.statespace.all_final_nodes())
        allocations = [frozenset(node.allocations)
                       if node.allocations else frozenset()
                       for node in final_nodes]
        self.deterministic_unallocated_memory = 0
        if not allocations:
            return
        all_allocations = frozenset.union(*allocations)
        deterministic = frozenset.intersection(*allocations)
        for a in sorted(all_allocations - deterministic):
            for node in final_nodes:
                if node.allocations and a in node.allocations:
                    gcontext = GlobalContext(None, node, None, generator=self)
                    m = errormsg.MemoryLeak(gcontext.get_context(a.pid),
                                            address=a.addr,
                                            size=a.size)
                    break
            else:
                assert 0  # This shoud not happen
            self.add_error_message(m)

        for a in deterministic:
            self.deterministic_unallocated_memory += a.size

    def final_check(self):
        if self.debug_compare_states is not None:
            self.debug_compare()
        for worker in self.workers:
            worker.before_final_check()
        for worker in self.workers:
            worker.final_check()

    def debug_compare(self):
        if self.debug_captured_states is None:
            self.debug_captured_states = []
        logging.info("%s states was captured", len(self.debug_captured_states))
        if len(self.debug_captured_states) < 2:
            return

        gstate1, worker1 = self.debug_captured_states[0]
        gstate2, worker2 = self.debug_captured_states[1]
        logging.info("Hashes %s, %s",
                     gstate1.compute_hash(), gstate2.compute_hash())
        for i, (s1, s2) in enumerate(zip(gstate1.states, gstate2.states)):
            if s1.vg_state and s2.vg_state:
                logging.info("Pid %s: hash1=%s hash2=%s",
                             i, s1.vg_state.hash, s2.vg_state.hash)
                if s1.vg_state.hash != s2.vg_state.hash:

                    controller = worker1.controllers[i]
                    controller.restore_state(s1.vg_state)
                    controller.debug_dump_state(s1.vg_state.id)

                    controller = worker2.controllers[i]
                    controller.restore_state(s2.vg_state)
                    controller.debug_dump_state(s2.vg_state.id)

                for name in s1.__dict__.keys():
                    if getattr(s1, name) != getattr(s2, name):
                        logging.info("stateA: %s %s", name, getattr(s1, name))
                        logging.info("stateB: %s %s", name, getattr(s2, name))

        for gstate, worker in self.debug_captured_states:
            gstate.dispose()

    """
    def add_node(self, prev, node):


    def add_node(self, prev, worker, gstate, do_hash=True):
        if do_hash:
            hash = gstate.compute_hash()
            if hash is not None:
                node = self.statespace.get_node_by_hash(hash)
                if node is not None:
                    return (node, False)
        else:
            hash = None
        uid = str(self.statespace.nodes_count)
        node = Node(uid, hash)
        logging.debug("New node %s", node.uid)

        if prev:
            node.prev = prev
        self.statespace.add_node(node)

        if self.debug_compare_states is not None \
                and node.uid in self.debug_compare_states:
            if self.debug_captured_states is None:
                self.debug_captured_states = []
            logging.debug("Capturing %s", node)
            self.debug_captured_states.append((gstate.copy(), worker))

        if self.statespace.nodes_count > self.max_states:
            logging.info("Maximal number of states reached")
            if self.debug_compare_states is not None:
                self.debug_compare()
            raise ErrorFound()

        if self.debug_state == uid:
            context = Context(self, node, None)
            context.add_error_and_throw(
                errormsg.StateCaptured(context, uid=uid))
        return (node, True)
    """

    def create_report(self, args, version):
        for error_message in self.error_messages:
            if error_message.node:
                if error_message.events is None:
                    error_message.events = \
                        self.statespace.events_to_node(error_message.node,
                                                       None)
                if self.stdout_mode == "capture":
                    error_message.stdout = \
                        [self.statespace.stream_to_node(
                            error_message.node,
                            None,
                            STREAM_STDOUT,
                            pid)
                         for pid in xrange(self.process_count)]
                if self.stderr_mode == "capture":
                    error_message.stderr = \
                        [self.statespace.stream_to_node(
                            error_message.node,
                            None,
                            STREAM_STDERR,
                            pid)
                         for pid in xrange(self.process_count)]
        return Report(self, args, version)



class GeneratorConnection(object):

    def __init__(self, port):
        s = socket.create_connection(("127.0.0.1", port))
        self.socket = SocketWrapper(s)
        self.socket.set_no_delay()

    def read_worker_id(self):
        return int(self.socket.read_line())

    def new_state(self, hash, n_actions):
        self.socket.send_data("STATE {} {}\n".format(hash, n_actions))

    def send_ports(self, ports):
        self.socket.send_data("{}\n".format(" ".join(map(str, ports))))

    def read_line(self):
        return self.socket.read_line()


class WorkerDescriptor(object):

    def __init__(self, generator, socket, worker_id):
        self.worker_id = worker_id
        self.generator = generator
        self.queue = deque()
        self.active_node = None
        s, addr = socket.accept()
        self.has_connection = [False] * self.generator.aislinn_args.workers
        self.socket = SocketWrapper(s)
        self.socket.set_no_delay()
        self.socket.send_data("{}\n".format(worker_id))

    def read_line(self):
        return self.socket.read_line()

    def fileno(self):
        return self.socket.socket.fileno()

    def send_command(self, command):
        self.socket.send_data(command)

    def check_connection(self, worker):
        if self.has_connection[worker.worker_id]:
            return
        assert worker != self
        self.send_command("LISTEN {}\n".format(worker.worker_id))
        ports = self.read_line()
        worker.send_command("CONNECT {} {}\n".format(self.worker_id, ports))

        worker.has_connection[self.worker_id] = True
        self.has_connection[worker.worker_id] = True

    def transfer_gstate(self, worker, hash):
        self.check_connection(worker)
        self.send_command("PUSH {} {}\n".format(worker.worker_id, hash))
        worker.send_command("POP {} {}\n".format(self.worker_id, hash))

    def start_next(self, response):
        if not self.queue:
            self.active_node = None
            self.send_command(response)
            return
        node, action = self.queue.pop()
        self.send_command("{}START {} {}\n".format(response, node.hash, action))
        self.active_node = node

    def process_command(self):
        command = self.read_line().split()
        name = command[0]
        if name == "STATE":
            node, is_new = self.generator.add_node(self.active_node, command[1])
            if is_new:
                response = "SAVE\n"
                n_actions = int(command[2])
                for action in xrange(n_actions):
                    self.queue.append((node, action))
            else:
                response = "DROP\n"
            self.start_next(response)
            #self.transfer_gstate(self.generator.workers[1], command[1])
        else:
            raise Exception("Unknown command: " + repr(command))


def poll_workers(workers):
    for worker in workers:
        if worker.socket.recv_buffer:
            return [worker]
    rlist, wlist, xlist = select.select(workers, (), ())
    return rlist


