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

import base.resource

import socket
import subprocess
import paths
import logging

class UnexpectedOutput(Exception):

    def __init__(self, output):
        self.output = output

    def __str__(self):
        return self.output

def check_str(value):
    if value:
        return "check"
    else:
        return "unsafe"


class Controller:

    # TODO: Universal architecture detection
    POINTER_SIZE = 8
    INT_SIZE = 4

    FUNCTION_INT = 0
    FUNCTION_4_POINTER = 1
    FUNCTION_2_INT_2_POINTER = 2
    FUNCTION_2_INT_4_POINTER = 3

    debug_under_valgrind = False
    profile_under_valgrind = False

    stdout_arg = None

    def __init__(self, args, cwd=None):
        self.process = None
        self.conn = None
        self.recv_buffer = ""
        self.args = tuple(args)
        self.cwd = cwd
        self.valgrind_args = ()
        self.server_socket = None

    def start(self, capture_syscalls=()):
        assert self.process is None # Nothing is running
        assert self.conn is None

        self.server_socket = self._start_server()
        port = self.server_socket.getsockname()[1]
        self._start_valgrind(port, capture_syscalls)

    def start_and_connect(self, *args, **kw):
        self.start(*args, **kw)
        return self.connect()

    def connect(self):
        self.server_socket.settimeout(0.3)
        try:
            self.conn, addr = self.server_socket.accept()
        except socket.timeout:
            logging.error("Aislinn client was not started")
            return None
        self.server_socket.close()
        self.server_socket = None
        return self.receive_line()

    def kill(self):
        if self.process and self.process.poll() is None:
            self.process.kill()
            self.process = None

    def run_process(self):
        return self.send_and_receive("RUN\n")

    def run_drop_syscall(self):
        return self.send_and_receive("RUN_DROP_SYSCALL\n")

    def run_function(self, fn_pointer, fn_type, *args):
        command = "RUN_FUNCTION {0} {1} {2} {3} \n".format(
                fn_pointer, fn_type, len(args), " ".join(map(str, args)))
        return self.send_and_receive(command)

    def client_malloc(self, size):
        return self.send_and_receive_int("CLIENT_MALLOC {0}\n".format(size))

    def client_free(self, mem):
        self.send_and_receive_ok("CLIENT_FREE {0}\n".format(mem))

    def client_malloc_from_buffer(self, buffer_id):
        return self.send_and_receive_int(
                "CLIENT_MALLOC_FROM_BUFFER {0}\n".format(buffer_id))

    def memcpy(self, addr, source, size, check=True):
        self.send_and_receive_ok("WRITE {0} {1} addr {2} {3}\n" \
                .format(check_str(check), addr, source, size))

    def write_into_buffer(self, buffer_addr, index, addr, size):
        self.send_and_receive_ok("WRITE_BUFFER {0} {1} {2} {3}\n" \
                    .format(buffer_addr, index, addr, size))

    def write_buffer(self, addr, buffer_addr,
                     index=None, size=None, check=True):
        if index is None or size is None:
            self.send_and_receive_ok("WRITE {0} {1} buffer {2}\n" \
                    .format(check_str(check), addr, buffer_addr))
        else:
            assert size is not None
            if size == 0:
                return
            self.send_and_receive_ok("WRITE {0} {1} buffer-part {2} {3} {4}\n" \
                    .format(check_str(check), addr, buffer_addr, index, size))

    def write_int(self, addr, value, check=True):
        self.send_and_receive_ok("WRITE {0} {1} int {2}\n" \
                .format(check_str(check), addr, value))

    def write_string(self, addr, value, check=True):
        self.send_and_receive_ok("WRITE {0} {1} string {2}\n" \
                .format(check_str(check), addr, value))


    def write_pointer(self, addr, value, check=True):
        self.send_and_receive_ok("WRITE {0} {1} pointer {2}\n" \
                .format(check_str(check), addr, value))

    def write_ints(self, addr, values, check=True):
        self.send_and_receive_ok("WRITE {0} {1} ints {2} {3}\n" \
                .format(check_str(check), addr, len(values), " ".join(map(str, values))))

    def read_mem(self, addr, size):
        return self.send_and_receive_data("READ {0} mem {1}\n" \
                .format(addr, size))

    def read_int(self, addr):
        return self.send_and_receive_int("READ {0} int\n".format(addr))

    def read_pointer(self, addr):
        return self.send_and_receive_int("READ {0} pointer\n".format(addr))

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

    def is_writable(self, addr, size):
        return self.send_and_receive("CHECK write {0} {1}\n".format(addr, size))

    def is_readable(self, addr, size):
        return self.send_and_receive("CHECK read {0} {1}\n".format(addr, size))

    def lock_memory(self, addr, size):
        self.send_and_receive_ok("LOCK {0} {1}\n".format(addr, size))

    def unlock_memory(self, addr, size):
        self.send_and_receive_ok("UNLOCK {0} {1}\n".format(addr, size))

    def get_allocations(self):
        self.send_command("ALLOCATIONS\n");
        result = []
        for line in self.receive_until_ok():
            addr, size = line.split()
            result.append((int(addr), int(size)))
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

    def receive_data(self):
        args = self.receive_result().split()
        keyword, size = args
        data_size = int(size)
        data = self.recv_buffer[:data_size]
        self.recv_buffer = self.recv_buffer[data_size:]
        remaining = data_size - len(data)
        while remaining > 0:
            self.recv_buffer = self.conn.recv(4096)
            data += self.recv_buffer[:remaining]
            self.recv_buffer = self.recv_buffer[remaining:]
            remaining = data_size - len(data)
        assert len(data) == data_size
        return data

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

    def send_and_receive_data(self, command):
        self.send_command(command)
        return self.receive_data()

    def send_and_receive_ok(self, command):
        self.send_command(command)
        r = self.receive_line()
        if r != "Ok":
            raise self.on_unexpected_output(r)

    def on_unexpected_output(self, line):
        raise UnexpectedOutput(line)

    def receive_until_ok(self):
        result = []
        line = self.receive_line()
        while line != "Ok":
            result.append(line)
            line = self.receive_line()
        return result

    def send_and_receive_int(self, command):
        return int(self.send_and_receive(command))

    def debug_compare(self, state_id1, state_id2):
        self.send_and_receive_ok(
             "DEBUG_COMPARE {0} {1}\n".format(state_id1, state_id2))

    def set_capture_syscall(self, syscall, value):
        self.send_and_receive_ok(
             "SET syscall {0} {1}\n".format(syscall, "on" if value else "off"))

    def save_state(self):
        return self.send_and_receive_int("SAVE\n")

    def restore_state(self, state_id):
        self.send_and_receive_ok("RESTORE {0}\n".format(state_id))

    def make_buffer(self, size):
        return self.send_and_receive_int("NEW_BUFFER {0}\n".format(size))

    def free_state(self, state_id):
        self.send_and_receive_ok("FREE {0}\n".format(state_id))

    def free_buffer(self, buffer_id):
        self.send_and_receive_ok("FREE_BUFFER {0}\n".format(buffer_id))

    def _start_valgrind(self, port, capture_syscalls):
        args = (
            paths.VALGRIND_BIN,
            "-q",
            "--tool=aislinn",
            "--port={0}".format(port)
        ) + tuple([ "--capture-syscall=" + name for name in capture_syscalls ]) \
          + tuple(self.valgrind_args) + tuple(self.args)

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

        logging.debug("Starting valgrind with %s", args)
        self.process = subprocess.Popen(
            args, cwd=self.cwd, stdout=self.stdout_arg)

    def _start_server(self):
        HOST = "127.0.0.1" # Connection only from localhost
        PORT = 0 # Alloc arbirary empty port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((HOST, PORT))
        s.listen(1)
        return s



class VgState(base.resource.Resource):
    hash = None

class VgBuffer(base.resource.Resource):
    hash = None


class ControllerWithResources(Controller):

    def __init__(self, args, cwd=None):
        Controller.__init__(self, args, cwd)
        self.states = base.resource.ResourceManager(VgState)
        self.buffers = base.resource.ResourceManager(VgBuffer)
        self.state_cache = {}

    @property
    def states_count(self):
        assert len(self.state_cache) == self.states.resource_count
        return self.states.resource_count

    @property
    def buffers_count(self):
        return self.buffers.resource_count

    def cleanup_states(self):
        if self.states.not_used_resources:
            for state in self.states.pickup_resources_to_clean():
                if state.hash:
                    del self.state_cache[state.hash]
                self.free_state(state.id)

    def cleanup_buffers(self):
        if self.buffers.not_used_resources:
            for b in self.buffers.pickup_resources_to_clean():
                self.free_buffer(b.id)

    def save_state(self, hash=None):
        if hash:
            state = self.state_cache.get(hash)
            if state:
                logging.debug("State %s retrieved from cache", hash)
                state.inc_ref_revive()
                return state
        state = self.states.new(Controller.save_state(self))
        if hash is not None:
            state.hash = hash
            self.state_cache[hash] = state
        return state

    def save_state_with_hash(self):
        return self.save_state(self.hash_state())

    def restore_state(self, state):
        Controller.restore_state(self, state.id)

    def make_buffer(self, size):
        return self.buffers.new(Controller.make_buffer(self, size))
