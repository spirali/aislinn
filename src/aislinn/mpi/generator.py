#
#    Copyright (C) 2014-2016 Stanislav Bohm
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
from wproxy import WorkerProxy
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



class Generator:

    def __init__(self, args, process_count, aislinn_args):
        self.args = args
        self.statespace = StateSpace()
        self.search_tasks = {}
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

        self.workers = None  # [WorkerProxy]
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

    def sleeping_neighbours(self, worker_id):
        for i in xrange(1, len(self.workers)):
            worker = self.workers[(i + worker_id) % len(self.workers)]
            if not worker.queue and not worker.active_node:
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

        workers = []
        for i in xrange(self.aislinn_args.workers):
            pid = os.fork()
            if pid != 0:
                s.close()
                worker = Worker(self.aislinn_args.workers,
                                port,
                                self.args,
                                self.aislinn_args,
                                self.process_count)
                worker.start_controllers()
                worker.connect_controllers()
                worker.run()
                sys.exit(0)

        workers = [WorkerProxy(self, s, i)
                   for i in xrange(self.aislinn_args.workers)]
        initial_node = Node("init", None)
        self.statespace.add_node(initial_node)
        self.statespace.initial_node = initial_node
        workers[0].active_node = initial_node
        self.workers = workers
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

    def run(self):
        self.init_time = datetime.datetime.now()
        try:
            if not self.start_workers():
                return False

            self.main_cycle()
            """
            self.memory_leak_check()
            if self.send_protocol == "full" and not self.error_messages:
                self.ndsync_check()
            """

            self.final_check()
            self.is_full_statespace = True

            for worker in self.workers:
                worker.quit()
        except ErrorFound:
            logging.debug("ErrorFound catched")
        finally:
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
        assert not self.search_tasks
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


def poll_workers(workers):
    for worker in workers:
        if worker.socket.recv_buffer:
            return [worker]
    rlist, wlist, xlist = select.select(workers, (), ())
    return rlist

