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

from base.resource import ResourceManager, Resource
from socketwrapper import SocketWrapper

import socket
import subprocess
import paths
import logging
import hashlib
import select


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
    buffer_server_port = None

    name = "" # For debug purpose

    def __init__(self, args, cwd=None):
        self.process = None
        self.socket = None
        self.recv_buffer = ""
        self.args = tuple(args)
        self.cwd = cwd
        self.valgrind_args = ()
        self.server_socket = None
        self.running = False

    def start(self, capture_syscalls=()):
        assert self.process is None # Nothing is running
        assert self.socket is None

        self.server_socket = self._start_server()
        port = self.server_socket.getsockname()[1]
        self._start_valgrind(port, capture_syscalls)

    def start_and_connect(self, *args, **kw):
        self.start(*args, **kw)
        self.connect()
        return self.receive_line()

    def connect(self):
        self.server_socket.settimeout(0.3)
        try:
            sock, addr = self.server_socket.accept()
        except socket.timeout:
            logging.error("Aislinn client was not started")
            return False
        self.socket = SocketWrapper(sock)
        self.socket.set_no_delay()
        self.server_socket.close()
        self.server_socket = None
        return True
        # User has to call receive_line after calling this method
        # But it may take some time to initialize vgclient, hence
        # it is not build in in connect to allow polling

    def kill(self):
        if self.process and self.process.poll() is None:
            self.process.kill()
            self.process = None

    def run_process(self):
        return self.send_and_receive("RUN\n")

    def run_drop_syscall(self):
        return self.send_and_receive("RUN_DROP_SYSCALL\n")

    def run_process_async(self):
        self.running = True
        self.send_command("RUN\n")

    def run_drop_syscall_async(self):
        self.running = True
        self.send_command("RUN_DROP_SYSCALL\n")

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
        # Copy a memory from client addres to the buffer
        self.send_and_receive_ok("WRITE_BUFFER {0} {1} {2} {3}\n" \
                    .format(buffer_addr, index, addr, size))

    def write_data_into_buffer(self, buffer_addr, index, data):
        # Write a literal data into the buffer
        size = len(data)
        if size == 0:
            return
        # TODO: the following constant should be benchmarked
        if size < 8192:
            self.send_data_and_receive_ok(
                    "WRITE_BUFFER_DATA {0} {1} {2}\n{3}" \
                            .format(buffer_addr, index, len(data), data))
        else:
            self.send_command("WRITE_BUFFER_DATA {0} {1} {2}\n" \
                        .format(buffer_addr, index, len(data)))
            self.send_data_and_receive_ok(data)

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
        return self.send_and_receive("ALLOCATIONS\n");

    ### Semi-internal functions

    def send_command(self, command):
        assert command[-1] == "\n", "Command does not end with new line"
        self.socket.send_data(command)

    def send_data(self, data):
       self.socket.send_data(data)

    def receive_line(self):
        line = self.socket.read_line()
        if line.startswith("Error:"):
            raise Exception("Received line: " + line)
        return line

    def finish_async(self):
        assert self.running
        self.running = False
        return self.receive_line()

    def receive_data(self):
        args = self.socket.read_line().split()
        return self.socket.read_data(int(args[1]))

    def send_and_receive(self, command):
        self.send_command(command)
        assert not self.running
        return self.receive_line()

    def send_and_receive_data(self, command):
        self.send_command(command)
        assert not self.running
        return self.receive_data()

    def send_and_receive_ok(self, command):
        self.send_command(command)
        assert not self.running
        r = self.receive_line()
        if r != "Ok":
            raise self.on_unexpected_output(r)

    def send_data_and_receive_ok(self, data):
        self.send_data(data)
        assert not self.running
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

    def make_buffer(self, buffer_id, size):
        self.send_and_receive_ok(
             "NEW_BUFFER {0} {1}\n".format(buffer_id, size))

    def start_remote_buffer(self, buffer_id):
        self.send_command("START_REMOTE_BUFFER {0}\n".format(buffer_id))

    def finish_remote_buffer(self):
        self.send_and_receive_ok("FINISH_REMOTE_BUFFER\n")

    def remote_buffer_upload(self, addr, size):
        self.send_command("UPLOAD {0} {1}\n".format(addr, size))

    def remote_buffer_download(self, buffer_id):
        self.send_command("DOWNLOAD {0}\n".format(buffer_id))

    def free_state(self, state_id):
        self.send_command("FREE {0}\n".format(state_id))

    def free_buffer(self, buffer_id):
        self.send_command("FREE_BUFFER {0}\n".format(buffer_id))

    def _start_valgrind(self, port, capture_syscalls):
        args = (
            paths.VALGRIND_BIN,
            "-q",
            "--tool=aislinn",
            "--port={0}".format(port)
        ) + tuple([ "--capture-syscall=" + name for name in capture_syscalls ])

        if self.buffer_server_port is not None:
            args += ("--bs-port={0}".format(self.buffer_server_port),)

        args += tuple(self.valgrind_args) + tuple(self.args)

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

    def __repr__(self):
        return "<Controller '{0}'>".format(self.name)


class ControllerResourceManager(ResourceManager):
    controller = None


class VgState(Resource):
    hash = None

    @property
    def controller(self):
        return self.manager.controller


class BufferManager(ResourceManager):

    def __init__(self):
        ResourceManager.__init__(self, VgBuffer)
        self.buffer_id_counter = 10

    def cleanup(self):
        if self.not_used_resources:
            for b in self.pickup_resources_to_clean():
                b.cleanup()

    def new_buffer(self, data):
        buffer_id = self.buffer_id_counter
        self.buffer_id_counter += 1
        buffer = self.new(buffer_id)
        buffer.set_data(data)
        # We add a special referece, this refence is
        # removed when buffer is written into all controllers
        # It may happen that state are disposed before this,
        # (usually when an error is detected)
        buffer.inc_ref()
        return buffer


class VgBuffer(Resource):

    def __init__(self, manager, id):
        Resource.__init__(self, manager, id)
        self.data = None
        self.size = None
        self.hash = None
        self.controllers = []
        self.remaining_controllers = None

    def cleanup(self):
        for controller in self.controllers:
            controller.free_buffer(self.id)

    def set_data(self, data):
        self.data = data
        hashthread = hashlib.md5()
        hashthread.update(self.data)
        self.hash = hashthread.hexdigest()
        self.size = len(data)

    def write_data(self, controller):
        logging.debug("Writing buffer %s into %s", self, controller)
        controller.make_buffer(self.id, self.size)
        controller.write_data_into_buffer(self.id, 0, self.data)
        self.controllers.append(controller)
        self.remaining_controllers -= 1
        if self.remaining_controllers <= 0:
            assert self.remaining_controllers == 0
            self.data = None
            # Remove reference added in BufferManager.new_buffer()
            self.dec_ref()

    def __repr__(self):
        return "<VgBuffer id={0.id} size={0.size} " \
               "ref_count={0.ref_count} rc={0.remaining_controllers}>".format(self)


class ControllerWithResources(Controller):

    def __init__(self, args, cwd=None):
        Controller.__init__(self, args, cwd)
        self.states = ControllerResourceManager(VgState)
        self.states.controller = self
        self.state_cache = {}
        self.buffers_to_make = []

    @property
    def states_count(self):
        assert len(self.state_cache) == self.states.resource_count
        return self.states.resource_count

    def cleanup_states(self):
        if self.states.not_used_resources:
            for state in self.states.pickup_resources_to_clean():
                if state.hash:
                    del self.state_cache[state.hash]
                self.free_state(state.id)


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

    def add_buffer(self, buffer):
        self.buffers_to_make.append(buffer)

    def make_buffers(self):
        if self.buffers_to_make:
            for buffer in self.buffers_to_make:
                buffer.write_data(self)
            self.buffers_to_make = []

    def fileno(self):
        return self.socket.socket.fileno()

def poll_controllers(controllers):
    for c in controllers:
        if c.socket.recv_buffer:
            return [ c ]
    rlist, wlist, xlist = select.select(controllers, (), ())
    return rlist
