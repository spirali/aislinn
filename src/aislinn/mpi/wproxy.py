#
#    Copyright (C) 2016 Stanislav Bohm
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


from base.arc import Arc

from vgtool.socketwrapper import SocketWrapper

from collections import deque
import logging

try:
    import cPickle as pickle
except:
    import pickle


class SearchTask(object):

    def __init__(self, node, n_actions, worker):
        self.node = node
        self.n_actions = n_actions
        self.workers = [worker]


class WorkerProxy(object):

    def __init__(self, generator, socket, worker_id):
        self.worker_id = worker_id
        self.generator = generator
        self.queue = deque()
        self.active_node = None
        s, addr = socket.accept()
        self.has_connection = [False] * self.generator.aislinn_args.workers

        self.socket = SocketWrapper(s)
        self.socket.set_no_delay()

        data = pickle.dumps((generator.aislinn_args, generator.run_args))
        self.socket.send_data("{} {}\n{}".format(worker_id, len(data), data))

        self.command_buffer = []

    def read_line(self):
        return self.socket.read_line()

    def fileno(self):
        return self.socket.socket.fileno()

    def send_command(self, command, now=False):
        self.command_buffer.append(command)
        if now:
            self.send_now()

    def send_now(self):
        if self.command_buffer:
            self.socket.send_data("".join(self.command_buffer))
            del self.command_buffer[:]

    def quit(self):
        self.send_command("QUIT\n", True)

    def final_check(self):
        assert not self.queue
        self.send_command("FINAL_CHECK\n", True)

    def free_state(self, hash):
        self.send_command("FREE {}\n".format(hash))

    def check_connection(self, worker):
        if self.has_connection[worker.worker_id]:
            return
        assert worker != self
        self.send_command("LISTEN {}\n".format(worker.worker_id), True)
        ports = self.read_line()
        worker.send_command("CONNECT {} {}\n".format(self.worker_id, ports), True)

        worker.has_connection[self.worker_id] = True
        self.has_connection[worker.worker_id] = True

    def transfer_gstate(self, worker, hash):
        print "---> Transfering {} => {} | {}".format(self.worker_id, worker.worker_id, hash)
        self.check_connection(worker)
        self.send_command("PUSH {} {}\n".format(worker.worker_id, hash), True)
        worker.send_command("PULL {} {}\n".format(self.worker_id, hash), True)

    def start_next(self):
        if not self.queue:
            self.active_node = None
            return

        while len(self.queue) > 2 or self.queue[0].n_actions > 1:
            worker = self.generator.sleeping_neighbours(self.worker_id)
            if worker is None:
                break
            task = self.queue[0]
            self.transfer_gstate(worker, task.node.hash)
            task.workers.append(worker)
            worker.queue.append(task)
            worker.start_next()
            worker.send_now()

        task = self.queue[0]
        node = task.node
        task.n_actions -= 1
        assert task.n_actions >= 0
        self.send_command("START {} {}\n".format(node.hash, task.n_actions))
        self.active_node = node

        if task.n_actions == 0:
            for worker in task.workers:
                worker.queue.remove(task)
                worker.free_state(task.node.hash)

    def process_command(self):
        command = self.read_line().split()
        name = command[0]
        if name == "STATE":
            hash = command[1]
            node, is_new = self.generator.add_node(self.active_node, hash)

            if is_new:
                n_actions = int(command[2])
                if n_actions >= 1:
                    task = SearchTask(node, n_actions, self)
                    #self.generator.search_tasks[hash] = task
                    self.queue.append(task)
                    self.send_command("SAVE\n")

            arc = Arc(node, None, None, None)
            arc.worker = self.worker_id
            self.active_node.add_arc(arc)
            self.start_next()
        else:
            raise Exception("Unknown command: " + repr(command))
        self.send_now()
