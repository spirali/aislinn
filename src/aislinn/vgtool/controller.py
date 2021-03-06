#
#    Copyright (C) 2014, 2015, 2016 Stanislav Bohm
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

from resource import ResourceManager, Resource
from socketwrapper import SocketWrapper

import socket
import subprocess
import logging
import hashlib
import select
import os


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
    """ The main class for controlling AVT - Aislinn Valgrind Tool

        Terminology:
        client - a verified process
        client's memory - a memory visible to a verified process
        buffer - a memory allocated in AVT by controller; invisible to client
    """


    # TODO: Universal architecture detection
    POINTER_SIZE = 8
    INT_SIZE = 4

    FUNCTION_INT = 0
    FUNCTION_4_POINTER = 1
    FUNCTION_2_INT_2_POINTER = 2
    FUNCTION_2_INT_4_POINTER = 3

    debug = False
    debug_by_valgrind_tool = None

    stdout_file = None
    stderr_file = None
    profile = False
    extra_env = None

    heap_size = None
    redzone_size = None
    verbose = None

    name = ""  # For debug purpose

    def __init__(self, valgrind_bin, args, cwd=None):
        self.process = None
        self.socket = None
        self.recv_buffer = ""
        self.args = tuple(args)
        self.cwd = cwd
        self.server_socket = None
        self.running = False
        self.valgrind_bin = valgrind_bin

    def start(self, capture_syscalls=()):
        """ Start Valgrind with Aislinn plugin (AVT)
        and initilizes connection """
        assert self.process is None  # Nothing is running
        assert self.socket is None

        self.server_socket = self._start_server()
        port = self.server_socket.getsockname()[1]
        self._start_valgrind(port, capture_syscalls)

    def connect(self):
        """ Connect to AVT """
        self.server_socket.settimeout(5.0)
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

    def start_and_connect(self, *args, **kw):
        """ Calls 'start' and 'connect' and receives the first line,
        returns None if connection failed"""
        self.start(*args, **kw)
        if not self.connect():
            return None
        return self.receive_line()

    def kill(self):
        """ Kills running AVT """
        if self.process and self.process.poll() is None:
            self.process.kill()
            self.process = None

    def set_capture_syscall(self, syscall, value):
        """ Switches on/off a capturing a syscall """
        self.send_and_receive_ok(
            "SET syscall {0} {1}\n".format(syscall, "on" if value else "off"))

    def save_state(self):
        """ Save a current process state """
        return self.send_and_receive_int("SAVE\n")

    def restore_state(self, state_id):
        """ Restores a saved process state """
        self.send_and_receive_ok("RESTORE {0}\n".format(state_id))

    def free_state(self, state_id):
        """ Frees a saved state """
        self.send_command("FREE {0}\n".format(state_id))

    def run_process(self):
        """ Resumes the paused process and wait until new event,
        then returns the event """
        return self.send_and_receive("RUN\n")

    def run_drop_syscall(self, return_value):
        """ When process is paused in syscall,
        it skips the syscall and then behaves as 'run' """
        return self.send_and_receive(
            "RUN_DROP_SYSCALL {0}\n".format(return_value))

    def run_process_async(self):
        """ Asynchronous version of 'run'. It does not wait for the
           next event and returns immediately """
        self.running = True
        self.send_command("RUN\n")

    def run_drop_syscall_async(self, return_value):
        """ Asynchornous version of 'run_drop_syscall'. It does not wait
           for the next event and retusn immediately. """
        self.running = True
        self.send_command("RUN_DROP_SYSCALL {0}\n".format(return_value))

    def finish_async(self):
        """ Finishes an asynchronous call """
        assert self.running
        self.running = False
        return self.receive_line()

    def run_function(self, fn_pointer, fn_type, *args):
        """ Executes a function in client """
        command = "RUN_FUNCTION {0} {1} {2} {3} \n".format(
                  fn_pointer, fn_type, len(args), " ".join(map(str, args)))
        return self.send_and_receive(command)

    def client_malloc(self, size):
        """ Calls "malloc" in client, i.e. allocate a memory
            that is visible for the verified process """
        return self.send_and_receive_int("CLIENT_MALLOC {0}\n".format(size))

    def client_free(self, mem):
        """ Calls "free" in client (an opposite function to client_malloc) """
        self.send_and_receive_ok("CLIENT_FREE {0}\n".format(mem))

    def client_malloc_from_buffer(self, buffer_id):
        """ Allocate a client's memory with the same size as buffer and
            copy buffer into this memory. """
        return self.send_and_receive_int(
            "CLIENT_MALLOC_FROM_BUFFER {0}\n".format(buffer_id))

    def memcpy(self, addr, source, size, check=True):
        """ Copies a non-overlapping block memory """
        self.send_and_receive_ok("WRITE {0} {1} addr {2} {3}\n"
                                 .format(check_str(check), addr, source, size))

    def write_into_buffer(self, buffer_id, index, addr, size):
        """ Writes a client memory into a buffer """
        # Copy a memory from client addres to the buffer
        self.send_and_receive_ok("WRITE_BUFFER {0} {1} {2} {3}\n"
                                 .format(buffer_id, index, addr, size))

    def write_data(self, addr, data, check=True):
        """ Writes data (str) into client's memory """
        size = len(data)
        if size == 0:
            return
        # TODO: the following constant should be benchmarked
        if size < 8192:
            command = "WRITE {0} {1} mem {2}\n{3}" \
                .format(check_str(check), addr, len(data), data)
            self.send_data_and_receive_ok(command)
        else:
            command = "WRITE {0} {1} mem {2}" \
                .format(check_str(check), addr, len(data))
            self.send_command(command)
            self.send_data_and_receive_ok(data)

    def write_data_into_buffer(self, buffer_addr, index, data):
        """ Writes data (str) into buffer """
        size = len(data)
        if size == 0:
            return
        # TODO: the following constant should be benchmarked
        if size < 8192:
            self.send_data_and_receive_ok(
                "WRITE_BUFFER_DATA {0} {1} {2}\n{3}"
                .format(buffer_addr, index, len(data), data))
        else:
            self.send_command("WRITE_BUFFER_DATA {0} {1} {2}\n"
                              .format(buffer_addr, index, len(data)))
            self.send_data_and_receive_ok(data)

    def write_buffer(self, addr, buffer_addr,
                     index=None, size=None, check=True):
        """ Copies a buffer into client's memory """
        if index is None or size is None:
            self.send_and_receive_ok(
                "WRITE {0} {1} buffer {2}\n"
                .format(check_str(check), addr, buffer_addr))
        else:
            assert size is not None
            if size == 0:
                return
            self.send_and_receive_ok(
                "WRITE {0} {1} buffer-part {2} {3} {4}\n"
                .format(check_str(check), addr, buffer_addr, index, size))

    def write_int(self, addr, value, check=True):
        """ Writes int into client's memory """
        self.send_and_receive_ok("WRITE {0} {1} int {2}\n"
                                 .format(check_str(check), addr, value))

    def write_string(self, addr, value, check=True):
        """ Writes string into client's memory """
        self.send_and_receive_ok("WRITE {0} {1} string {2}\n"
                                 .format(check_str(check), addr, value))

    def write_pointer(self, addr, value, check=True):
        """ Writes pointer into client's memory """
        self.send_and_receive_ok("WRITE {0} {1} pointer {2}\n"
                                 .format(check_str(check), addr, value))

    def write_ints(self, addr, values, check=True):
        """ Writes an array of ints into client's memory """
        self.send_and_receive_ok(
            "WRITE {0} {1} ints {2} {3}\n"
            .format(check_str(check),
                    addr,
                    len(values),
                    " ".join(map(str, values))))

    def read_mem(self, addr, size):
        """ Reads client's memory """
        return self.send_and_receive_data("READ {0} mem {1}\n"
                                          .format(addr, size))

    def read_int(self, addr):
        """ Reads int from client's memory """
        return self.send_and_receive_int("READ {0} int\n".format(addr))

    def read_pointer(self, addr):
        """ Reads pointer from client's memory """
        return self.send_and_receive_int("READ {0} pointer\n".format(addr))

    def read_ints(self, addr, count):
        """ Reads an array of ints from client's memory """
        line = self.send_and_receive("READ {0} ints {1}\n".format(addr, count))
        results = map(int, line.split())
        assert len(results) == count
        return results

    def read_pointers(self, addr, count):
        """ Reads an array of pointers from client's memory """
        line = self.send_and_receive("READ {0} pointers {1}\n"
                                     .format(addr, count))
        results = map(int, line.split())
        assert len(results) == count
        return results

    def read_string(self, addr):
        """ Reads a string from client's memory """
        return self.send_and_receive_data("READ {0} string\n".format(addr))

    def read_buffer(self, buffer_id):
        """ Reads a buffer """
        return self.send_and_receive_data("READ_BUFFER {0}\n"
                                          .format(buffer_id))

    def hash_state(self):
        """ Hashes current process state """
        h = self.send_and_receive("HASH\n")
        return h

    def hash_buffer(self, buffer_id):
        """ Hashes a buffer """
        return self.send_and_receive("HASH_BUFFER {0}\n".format(buffer_id))

    def get_stacktrace(self):
        """ Returns stack trace (each item separeted by ';') """
        return self.send_and_receive("STACKTRACE\n")

    def get_stats(self):
        """ Gets internal statistic from client
           (number of states, buffers, etc ...) """
        self.send_command("STATS\n")
        result = {}
        for entry in self.receive_line().split("|"):
            name, value = entry.split()
            result[name] = int(value)
        return result

    def is_writable(self, addr, size):
        """ Returns True if an client's address is writable """
        return self.send_and_receive("CHECK write {0} {1}\n"
                                     .format(addr, size))

    def is_readable(self, addr, size):
        """ Returns True if an client's address is readable """
        return self.send_and_receive("CHECK read {0} {1}\n".format(addr, size))

    def lock_memory(self, addr, size):
        """ Marks a client's memory as read only """
        self.send_and_receive_ok("LOCK {0} {1}\n".format(addr, size))

    def unlock_memory(self, addr, size):
        """ Marks a client's memory as defined """
        self.send_and_receive_ok("UNLOCK {0} {1}\n".format(addr, size))

    def get_allocations(self):
        """ Get list of client's allocations on heap """
        return self.send_and_receive("ALLOCATIONS\n")

    def interconn_listen(self):
        """ Clients start to listen for a connection on a free port,
            that is returned from the method.
            This blocks AVT but not controller.
            Method 'interconn_listen_finish' has to be called
            after this method """
        port = self.send_and_receive_int("CONN_LISTEN\n")
        self.running = True
        return port

    def interconn_listen_finish(self):
        """ This has to be called after interconn_listen.
            It blocks until the client is not connected and then
            returns socket id """
        return int(self.finish_async())

    def interconn_connect(self, host):
        """ Initializes a connection to another AVT that is listening by
            'interconn_listen'. This has be followed by
            'interconn_connect_finish'. """
        self.running = True
        return self.send_command("CONN_CONNECT {0}\n".format(host))

    def interconn_connect_finish(self):
        """ This method has to follow 'interconn_connect'.
            Blocks until connection is not finished.
            Returns socket id."""
        return int(self.finish_async())

    def push_state(self, socket, state_id):
        """ Send a state through an AVT interconnection """
        self.send_command("CONN_PUSH_STATE {0} {1}\n".format(socket, state_id))

    def pull_state(self, socket):
        """ Receives a state through an AVT interconnection """
        return self.send_and_receive_int("CONN_PULL_STATE {0}\n"
                                         .format(socket))

    def send_command(self, command):
        """ Send a command to AVT """
        assert command[-1] == "\n", "Command does not end with new line"
        self.socket.send_data(command)

    def send_data(self, data):
        """ Send data to AVT """
        self.socket.send_data(data)

    def receive_line(self):
        """ Receives a line (string) from AVT """
        line = self.socket.read_line()
        if line.startswith("Error:"):
            raise Exception("Received line: " + line)
        return line

    def receive_data(self):
        """ Receives a data from AVT """
        args = self.socket.read_line().split()
        return self.socket.read_data(int(args[1]))

    def send_and_receive(self, command):
        """ Sends a command and waits for the answer."""
        self.send_command(command)
        assert not self.running
        return self.receive_line()

    def send_and_receive_data(self, command):
        """ Sends a command and waits for the answer as data."""
        self.send_command(command)
        assert not self.running
        return self.receive_data()

    def send_and_receive_ok(self, command):
        """ Sends a command and waits for its confirmation (string "Ok\n") """
        self.send_command(command)
        assert not self.running
        r = self.receive_line()
        if r != "Ok":
            raise self.on_unexpected_output(r)

    def send_data_and_receive_ok(self, data):
        """ Sends data and waits for its confirmation (string "Ok\n") """
        self.send_data(data)
        assert not self.running
        r = self.receive_line()
        if r != "Ok":
            raise self.on_unexpected_output(r)

    def on_unexpected_output(self, line):
        """ This method is called when unexpected output is received,
            by default it throws UnexpectedOutput exception"""
        raise UnexpectedOutput(line)

    def receive_until_ok(self):
        """ Receives lines until "Ok" is not received """
        result = []
        line = self.receive_line()
        while line != "Ok":
            result.append(line)
            line = self.receive_line()
        return result

    def send_and_receive_int(self, command):
        """ Sends a command and waits for int """
        return int(self.send_and_receive(command))

    def debug_compare(self, state_id1, state_id2):
        """ Compares two saved states in AVT """
        self.send_and_receive_ok("DEBUG_COMPARE {0} {1}\n"
                                 .format(state_id1, state_id2))

    def debug_dump_state(self, state_id):
        """ Dumps a saved state on stderr """
        self.send_and_receive_ok("DEBUG_DUMP_STATE {0}\n"
                                 .format(state_id))

    def make_buffer(self, buffer_id, size):
        """ Creates a new buffer """
        self.send_and_receive_ok("NEW_BUFFER {0} {1}\n"
                                 .format(buffer_id, size))

    def free_buffer(self, buffer_id):
        """ Frees a buffer """
        self.send_command("FREE_BUFFER {0}\n".format(buffer_id))

    def _start_valgrind(self, port, capture_syscalls):
        args = (
            self.valgrind_bin,
            "-q",
            "--tool=aislinn",
            "--port={0}".format(port),
            "--identification={0}".format(self.name),
        ) + tuple(["--capture-syscall=" + name for name in capture_syscalls])

        if self.profile:
            args += ("--profile=yes",)

        if self.heap_size is not None:
            args += ("--heap-size={0}".format(self.heap_size),)

        if self.redzone_size is not None:
            args += ("--alloc-redzone-size={0}".format(self.redzone_size),)

        if self.verbose is not None:
            args += ("--verbose={0}".format(self.verbose),)

        args += self.args

        if self.debug_by_valgrind_tool:
            args = (
                "valgrind",
                "--tool=" + self.debug_by_valgrind_tool,
                "--sim-hints=enable-outer",
                "--trace-children=yes",
                "--smc-check=all-non-file",
                "--run-libc-freeres=no") + args

        logging.debug("Starting valgrind with %s", args)

        if self.extra_env:
            env = os.environ.copy()
            for v in self.extra_env:
                env[v] = self.extra_env[v]
        else:
            env = None
        self.process = subprocess.Popen(
            args, cwd=self.cwd, env=env,
            stdout=self.stdout_file, stderr=self.stderr_file)

    def _start_server(self):
        HOST = "127.0.0.1"  # Connection only from localhost
        PORT = 0  # Alloc arbirary empty port
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

    def __repr__(self):
        return "<VgState {0:x} id={1.id} " \
               "ctrl={1.controller.name} hash={1.hash}>" \
               .format(id(self), self)


class BufferManager(ResourceManager):

    def __init__(self, init_value, step):
        ResourceManager.__init__(self, VgBuffer)
        self.buffer_id_counter = init_value
        self.buffer_id_step = step

    def cleanup(self):
        if self.not_used_resources:
            for b in self.pickup_resources_to_clean():
                b.cleanup()

    def new_buffer(self, data):
        buffer_id = self.buffer_id_counter
        self.buffer_id_counter += self.buffer_id_step
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
        logging.debug("New buffer: %s", self)

    def cleanup(self):
        logging.debug("Cleaning buffer: %s", self)
        for controller in self.controllers:
            controller.free_buffer(self.id)
        self.controllers = None

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
        return "<VgBuffer id={0.id} size={0.size} ref_count={0.ref_count} " \
               "rc={0.remaining_controllers}>".format(self)


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

    def get_cached_state(self, hash):
        return self.state_cache.get(hash)

    def pull_state(self, socket, hash=None):
        state = self.states.new(Controller.pull_state(self, socket))
        if self.debug:
            self.restore_state(state)
            assert hash == self.hash_state()
        if hash is not None:
            state.hash = hash
            self.state_cache[hash] = state
        return state

    def push_state(self, socket, state):
        self.hash_state()
        Controller.push_state(self, socket, state.id)

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
            return [c]
    rlist, wlist, xlist = select.select(controllers, (), ())
    return rlist


def make_interconnection(controllers):
    sockets = []
    for i, c in enumerate(controllers):
        s = []
        for j, d in enumerate(controllers[:i]):
            port = c.interconn_listen()
            host = "127.0.0.1:{0}".format(port)
            d.interconn_connect(host)
            s.append(c.interconn_listen_finish())
            sockets[j].append(d.interconn_connect_finish())
        s.append(None)
        sockets.append(s)
    return sockets


def make_interconnection_pairs(controllers1, controllers2):
    ports = [c.interconn_listen() for c in controllers1]
    for port, c in zip(ports, controllers2):
        host = "127.0.0.1:{0}".format(port)
        c.interconn_connect(host)
    return ([c.interconn_listen_finish() for c in controllers1],
            [c.interconn_connect_finish() for c in controllers2])
