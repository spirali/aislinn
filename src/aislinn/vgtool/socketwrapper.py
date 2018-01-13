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

import socket


class SocketWrapper:

    def __init__(self, socket):
        self.socket = socket
        self.recv_buffer = ""

    def is_line_buffered(self):
        return "\n" in self.recv_buffer

    def read_line(self):
        b = self.recv_buffer
        while True:
            p = b.find("\n")
            if p != -1:
                self.recv_buffer = b[p + 1:]
                return b[:p]
            new = self.socket.recv(4096)
            if not new:
                raise Exception("Connection closed")
            b += new
            if len(b) > 409600:
                raise Exception("Line too long")

    def read_data(self, size):
        b = self.recv_buffer
        if b:
            if len(b) >= size:
                self.recv_buffer = b[size:]
                return b[:size]
            data = [b]
            size -= len(b)
            self.recv_buffer = ""
        else:
            data = []
        while size > 0:
            new = self.socket.recv(size)
            if not new:
                raise Exception("Connection closed")
            data.append(new)
            size -= len(new)
        return "".join(data)

    def send_data(self, data):
        self.socket.sendall(data)

    def set_no_delay(self):
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
