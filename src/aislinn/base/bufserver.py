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

from socketwrapper import SocketWrapper

from multiprocessing import Process, Queue
import logging
import select
import socket


class Server():

    def __init__(self, clients_count, port=0):
        self.clients_count = clients_count
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(("127.0.0.1", port))
        self.server_socket.listen(clients_count)
        self.clients = []
        self.buffers = {}

    @property
    def port(self):
        return self.server_socket.getsockname()[1]

    def handle_accept(self):
        socket, address = self.server_socket.accept()
        logging.debug("Client for bufserver accepted")
        self.clients.append(Client(self, SocketWrapper(socket)))

    def main(self):
        for i in xrange(self.clients_count):
            self.handle_accept()
        while True:
            sockets = [ client.socket.socket for client in self.clients ]
            rlist, wlist, xlist = select.select(sockets, (), ())
            for socket in rlist:
                for client in self.clients:
                    if client.socket.socket == socket:
                        client.handle_read()
                        break


class Client:

    def __init__(self, server, socket):
        self.server = server
        self.socket = socket

    def handle_read(self):
        self.process_command()
        while self.socket.is_line_buffered():
            self.process_command()

    def create_new_buffer(self, name):
        buffer_parts = []
        size = 0
        while True:
            line = self.socket.read_line()
            if line == "DONE":
                break
            s = int(line)
            buffer_parts.append(self.socket.read_data(s))
            size += s
        assert name not in self.server.buffers
        buffer_parts.insert(0, "{0}\n".format(size))
        self.server.buffers[name] = "".join(buffer_parts)

    def send_buffer(self, name):
        self.socket.send_data(self.server.buffers[name])

    def free_buffer(self, name):
        del self.server.buffers[name]

    def send_stats(self):
        count = len(self.server.buffers)
        size = sum(len(b) for b in self.server.buffers.values())
        self.socket.send_data("{0} {1}\n".format(count, size))

    def process_command(self):
        parts = self.socket.read_line().split()
        command = parts[0]

        if command == "GET":
            self.send_buffer(parts[1])
            return

        if command == "NEW":
            self.create_new_buffer(parts[1])
            return

        if command == "FREE":
            self.free_buffer(parts[1])
            return

        if command == "STATS":
            self.send_stats()
            return
        raise "Invalid command"


def _process_main(clients_count, queue):
    server = Server(clients_count)
    queue.put(server.port)
    server.main()

def start_process(clients_count):
    q = Queue(1)
    p = Process(target=_process_main, args=(clients_count, q))
    p.start()
    return p, q.get()

def connect(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", port))
    return SocketWrapper(s)
