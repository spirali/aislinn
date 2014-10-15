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


import socket
import subprocess
import paths
import time

class Controller:

    debug_under_valgrind = False
    profile_under_valgrind = False

    def __init__(self, args, cwd=None):
        self.process = None
        self.conn = None
        self.recv_buffer = ""
        self.args = tuple(args)
        self.cwd = cwd
        self.valgrind_args = ()

    def start(self):
        assert self.process is None # Nothing is running
        assert self.conn is None

        s = self._start_server()
        port = s.getsockname()[1]
        self._start_valgrind(port)

        # Give valgrind time to initialize, we definitely need a better system
        time.sleep(0.1)
        if self.process.poll():
            return None

        self.conn, addr = s.accept()
        return self.receive_line()

    def kill(self):
        if self.process:
            self.process.kill()
            self.process = None

    def save_state(self):
        return self.send_and_receive_int("SAVE\n")

    def free_state(self, state_id):
        self.send_and_receive_ok("FREE {0}\n".format(state_id))

    def run_process(self):
        return self.send_and_receive("RUN\n")

    def run_function(self, fn_pointer, fn_type, *args):
        command = "RUN_FUNCTION {0} {1} {2} {3} \n".format(
                fn_pointer, fn_type, len(args), " ".join(map(str, args)))
        return self.send_and_receive(command)

    def restore_state(self, state_id):
        assert state_id is not None
        return self.send_and_receive_ok("RESTORE {0}\n".format(state_id))

    def new_buffer(self, size):
        return self.send_and_receive_int("NEW_BUFFER {0}\n".format(size))

    def free_buffer(self, buffer_id):
        self.send_and_receive_ok("FREE_BUFFER {0}\n".format(buffer_id))

    def memcpy(self, addr, source, size):
        self.send_and_receive_ok("WRITE {0} addr {1} {2}\n" \
                .format(addr, source, size))

    def write_buffer(self, addr, buffer_addr, index=None, size=None):
        if index is None or size is None:
            self.send_and_receive_ok("WRITE {0} buffer {1}\n" \
                    .format(addr, buffer_addr))
        else:
            assert size is not None
            if size == 0:
                return
            self.send_and_receive_ok("WRITE {0} buffer-part {1} {2} {3}\n" \
                    .format(addr, buffer_addr, index, size))

    def write_into_buffer(self, buffer_addr, index, addr, size):
        self.send_and_receive_ok("WRITE_BUFFER {0} {1} {2} {3}\n" \
                    .format(buffer_addr, index, addr, size))

    def write_int(self, addr, value):
        self.send_and_receive_ok("WRITE {0} int {1}\n".format(addr, value))

    def write_ints(self, addr, values):
        self.send_and_receive_ok("WRITE {0} ints {1} {2}\n" \
                .format(addr, len(values), " ".join(map(str, values))))

    def reduce(self, addr, datatype, count, op, buffer_id):
        self.send_and_receive_ok("REDUCE {0} {1} {2} {3} {4}\n" \
                .format(addr, datatype, count, op, buffer_id))

    def read_int(self, addr):
        return self.send_and_receive_int("READ {0} int\n".format(addr))

    def read_ints(self, addr, count):
        line = self.send_and_receive("READ {0} ints {1}\n".format(addr, count))
        results = map(int, line.split())
        assert len(results) == count
        return results

    def read_pointers(self, addr, count):
        line = self.send_and_receive("READ {0} pointers {1}\n" \
                .format(addr, count))
        results = map(int, line.split())
        assert len(results) == count
        return results

    def hash_state(self):
        #s = time.time()
        h = self.send_and_receive("HASH\n")
        #e = time.time()
        #print e - s
        return h

    def hash_buffer(self, buffer_id):
        return self.send_and_receive("HASH_BUFFER {0}\n".format(buffer_id))

    def get_stacktrace(self):
        return self.send_and_receive("STACKTRACE\n")

    def get_stats(self):
        self.send_command("STATS\n")
        result = {}
        for entry in self.receive_line().split("|"):
            name, value = entry.split()
            result[name] = int(value)
        return result

    ### Semi-internal functions

    def receive_line(self):
        b = self.recv_buffer
        while True:
            p = b.find("\n")
            if p != -1:
                self.recv_buffer = b[p + 1:]
                return b[:p]
            new = self.conn.recv(4096)
            if not new:
                raise Exception("Connection closed")
            b += new
            if len(b) > 40960:
                raise Exception("Message too long")

    def send_command(self, command):
        assert command[-1] == "\n", "Command does not end with new line"
        self.conn.sendall(command)

    def receive_result(self):
        line = self.receive_line()
        if line.startswith("Error:"):
            raise Exception("Received line: " + line)
        return line

    def send_and_receive(self, command):
        self.send_command(command)
        return self.receive_result()

    def send_and_receive_ok(self, command):
        self.send_command(command)
        r = self.receive_line()
        if r != "Ok":
            raise Exception("Received line is to ok: " + r)

    def send_and_receive_int(self, command):
        return int(self.send_and_receive(command))

    def _start_valgrind(self, port):
        args = (
            paths.VALGRIND_BIN,
            "-q",
            "--tool=aislinn",
            "--port={0}".format(port)
        ) + tuple(self.valgrind_args) + tuple(self.args)

        if self.debug_under_valgrind or self.profile_under_valgrind:
            if self.profile_under_valgrind:
                extra = ("--tool=callgrind",)
            else:
                extra = ()

            args = (
                "valgrind",
                "--sim-hints=enable-outer",
                "--trace-children=yes",
                "--smc-check=all-non-file",
                "--run-libc-freeres=no") + extra + args

        self.process = subprocess.Popen(args, cwd=self.cwd)

    def _start_server(self):
        HOST = "127.0.0.1" # Connection only from localhost
        PORT = 0 # Alloc arbirary empty port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((HOST, PORT))
        s.listen(1)
        return s
