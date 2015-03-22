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

from base.stream import STREAM_STDOUT, STREAM_STDERR
from base.utils import convert_type
import errormsg
import consts
import ops
import logging
import mpicalls
import event


class Allocation:

    def __init__(self, pid, addr, size):
        self.pid = pid
        self.addr = addr
        self.size = size

    def compute_hash(self, hashthread):
        hashthread.update("{} {} {}".format(self.pid, self.addr, self.size))


class Context:

    def __init__(self, gcontext, state):
        self.gcontext = gcontext
        self.controller = None
        self.state = state
        self.fn_name = None
        self.event = None

    @property
    def gstate(self):
        return self.gcontext.gstate

    @property
    def generator(self):
        return self.gcontext.generator

    def save_state_with_hash(self):
        self.state.vg_state = self.controller.save_state_with_hash()

    def add_error_message(self, error_message):
        self.gcontext.add_error_message(error_message)

    def add_error_and_throw(self, error_message):
        self.gcontext.add_error_and_throw(error_message)

    def process_syscall(self, commands):
        if commands[1] == "write":
            gcontext = self.gcontext
            fd, data_ptr, size = commands[2:]
            if fd == "2" and self.gcontext.generator.stderr_mode != "stdout":
                if gcontext.generator.stderr_mode == "capture":
                    gcontext.add_stream_chunk(
                            STREAM_STDERR, self.state.pid,
                            self.controller.read_mem(data_ptr,
                                                     size))
                return self.gcontext.generator.stderr_mode == "print"
            if fd == "1" or (fd == "2"
                             and gcontext.generator.stderr_mode == "stdout"):
                if gcontext.generator.stdout_mode == "capture":
                    gcontext.add_stream_chunk(
                            STREAM_STDOUT, self.state.pid,
                            self.controller.read_mem(data_ptr,
                                                     size))
                return gcontext.generator.stdout_mode == "print"
            return True
        else:
            raise Exception("Invalid syscall" + commands[1])

    def handle_call(self, name, args, callback=False):
        call = mpicalls.calls_non_communicating.get(name)
        if call is None:
            call = mpicalls.calls_communicating.get(name)
            if callback:
                self.add_error_and_throw(errormsg.CommunicationInCallback(self))
        if call is not None:
            logging.debug("Call %s %s", name, args)
            return call.run(self, args)
        else:
            raise Exception("Unkown function call: {0} {1}".format(name, repr(args)))

    def restore_state(self):
        # Restore the state and forget about the restored state
        # The state is forgotten because we are going to modify it
        assert self.controller is None
        self.controller = self.gcontext.generator.get_controller(self.state.pid)
        # Register context into controller to capture unexpected outputs
        self.controller.context = self
        self.controller.restore_state(self.state.vg_state)
        self.state.vg_state.dec_ref()
        self.state.vg_state = None

    def run(self):
        controller = self.controller
        result = controller.run_process().split()
        while True:
            if result[0] == "CALL":
                if self.handle_call(result[1], result[2:]):
                    break
                else:
                    result = controller.run_process().split()
                    continue
            if result[0] == "SYSCALL":
                if self.process_syscall(result):
                    result = controller.run_process().split()
                else:
                    result = controller.run_drop_syscall().split()
                continue
            if result[0] == "EXIT":
                exitcode = convert_type(result[1], "int")
                e = event.ExitEvent(self.state.pid, exitcode)
                self.gcontext.add_event(e)
                self.state.set_finished()
                if exitcode != 0:
                    self.add_error_and_throw(
                            errormsg.NonzeroExitCode(self, exitcode=exitcode))
                self.state.allocations = \
                    [ Allocation(self.state.pid, addr, size)
                      for addr, size in self.controller.get_allocations() ]
                return
            if result[0] == "REPORT":
                self.add_error_and_throw(
                        self.make_error_message_from_report(result))
            raise Exception("Invalid command " + result[0])

    def make_error_message_from_report(self, parts):
        assert parts[0] == "REPORT"
        name = parts[1]
        if name == "heaperror":
            assert len(parts) == 2
            return errormsg.HeapExhausted(self)
        elif name == "invalidwrite":
            assert len(parts) == 4
            addr = int(parts[2], 16)
            size = int(parts[3])
            return errormsg.InvalidWrite(self, address=addr, size=size)
        elif name == "invalidwrite-locked":
            assert len(parts) == 4
            addr = int(parts[2], 16)
            size = int(parts[3])
            return errormsg.InvalidWriteLocked(self, address=addr, size=size)
        else:
            raise Exception("Unknown runtime error: " + name)

    def make_node(self):
        self.gcontext.make_node()

    def make_fail_node(self):
        self.gcontext.make_fail_node()

    def run_and_make_node(self):
        self.run()
        self.gcontext.make_node()

    def initial_run(self):
        controller = self.gcontext.generator.get_controller(self.state.pid)
        controller.context = self
        self.controller = controller
        result = controller.receive_line()
        if result is None:
            return False

        while True:
            result = result.split()
            if result[0] == "EXIT":
                exitcode = convert_type(result[1], "int")
                if exitcode != 0:
                    self.add_error_message(
                            errormsg.NonzeroExitCode(self, exitcode=exitcode))
                    return True
                else:
                    e = errormsg.NoMpiCall(self)
                    self.add_error_and_throw(e)
                return True
            elif result[0] == "REPORT":
                e = self.make_error_message_from_report(result)
                self.add_error_and_throw(e)
                return True
            elif result[0] == "SYSCALL":
                if self.process_syscall(result):
                    result = controller.run_process()
                else:
                    result = controller.run_drop_syscall()
            elif result[0] == "CALL":
                if result[1] == "MPI_Initialized":
                    assert len(result) == 3
                    ptr = convert_type(result[2], "ptr")
                    controller.write_int(ptr, 0)
                    result = controller.run_process()
                    continue
                elif result[1] != "MPI_Init":
                    e = errormsg.NoMpiInit(self)
                    self.add_error_and_throw(e)
                    return True
                break
            else:
                assert 0, "Invalid reposponse " + result

        # FIXME: Consts pool
        self.gcontext.generator.consts_pool = convert_type(result[4], "ptr")
        controller.write_int(self.gcontext.generator.get_const_ptr(
            consts.MPI_TAG_UB), 0xFFFF)
        function_ptrs = result[5:] # skip CALL MPI_Init argc argv consts_pool

        # The order of the ops is important,
        # because it has to be synchronous with code in MPI_Init
        operations = [ consts.MPI_SUM,
                       consts.MPI_PROD,
                       consts.MPI_MIN,
                       consts.MPI_MAX,
                       consts.MPI_LAND,
                       consts.MPI_LOR,
                       consts.MPI_BAND,
                       consts.MPI_BOR,
                       consts.MPI_MINLOC,
                       consts.MPI_MAXLOC ]

        assert len(function_ptrs) == len(ops.buildin_operations)
        assert len(function_ptrs) == len(operations)

        for ptr, op_id in zip(function_ptrs, operations):
            ops.buildin_operations[op_id].fn_ptr = ptr
        return True

    def run_function(self, fn_pointer, fn_type, *args):
        result = self.controller.run_function(fn_pointer, fn_type, *args)
        while result != "FUNCTION_FINISH":
            result = result.split()
            if result[0] == "EXIT":
                e = errormsg.ExitInCallback(self)
                self.add_error_and_throw(e)
            assert result[0] == "CALL"
            assert not self.handle_call(result[1], result[2:], True)
            result = self.controller.run_process()

    def on_unexpected_output(self, line):
        e = self.make_error_message_from_report(line.split())
        self.add_error_and_throw(e)

    def copy_comm_attrs(self, comm, new_comm):
        controller = self.controller
        for keyval, value in self.state.get_comm_attrs(comm):
            if keyval.copy_fn == consts.MPI_NULL_COPY_FN:
                continue
            tmp = controller.client_malloc(controller.POINTER_SIZE + \
                                           controller.INT_SIZE)
            value_out_ptr = tmp
            flag_ptr = tmp + controller.POINTER_SIZE

            self.run_function(
                keyval.copy_fn,
                controller.FUNCTION_2_INT_4_POINTER,
                comm.comm_id, keyval.keyval_id, keyval.extra_ptr,
                value, value_out_ptr, flag_ptr)

            if controller.read_int(flag_ptr):
                self.state.set_attr(self, new_comm, keyval,
                                    controller.read_pointer(value_out_ptr))
            controller.client_free(tmp)

    def make_buffer(self, pointer, datatype, count):
        data = []
        datatype.pack2(self.controller, pointer, count, data.append)
        return self.gcontext.generator.buffer_manager.new_buffer("".join(data))

    def make_buffer_for_one(self, pid, pointer, datatype, count):
        buffer = self.make_buffer(pointer, datatype, count)
        buffer.remaining_controllers = 1
        controller = self.gcontext.generator.get_controller(pid)
        controller.add_buffer(buffer)
        return buffer

    def make_buffer_for_more(self, pids, pointer, datatype, count):
        buffer = self.make_buffer(pointer, datatype, count)
        buffer.remaining_controllers = len(pids)
        for pid in pids:
            controller = self.gcontext.generator.get_controller(pid)
            controller.add_buffer(buffer)
        return buffer

    def close_all_requests(self):
        if not self.state.tested_request_ids:
            return
        self.close_requests(range(len(self.state.tested_request_ids)))

    def close_requests(self, indices):
        for i, index in enumerate(indices):
            request_id = self.state.tested_request_ids[index]
            if request_id == consts.MPI_REQUEST_NULL: # requests was MPI_REQUEST_NULL
                continue
            request = self.state.get_finished_request(request_id)
            self._close_request(request, index, i)
        self.tested_request_ids = None

    def _close_request(self, request, index_pointer, index_status):
        logging.debug("Closing request %s", request)
        if not self.state.immediate_wait and \
            ((request.is_send() and request.target != consts.MPI_PROC_NULL)
              or (request.is_receive() and request.source != consts.MPI_PROC_NULL)):
            request.datatype.lock_memory(self.controller,
                                         request.data_ptr,
                                         request.count, unlock=True)

        if self.state.tested_requests_pointer is not None and \
                self.state.get_persistent_request(request.id) is None:
            self.controller.write_int(
                    self.state.tested_requests_pointer + \
                    self.controller.REQUEST_SIZE * index_pointer,
                    consts.MPI_REQUEST_NULL)

        if self.state.tested_requests_status_ptr is not None and request.is_receive():
            status_ptr = self.state.tested_requests_status_ptr + \
                         self.controller.STATUS_SIZE * index_status
            if request.source == consts.MPI_PROC_NULL:
                self.controller.write_status(status_ptr,
                                             consts.MPI_PROC_NULL,
                                             consts.MPI_ANY_TAG,
                                             0)
            else:
                self.controller.write_status(status_ptr,
                                             request.source_rank,
                                             request.source_tag,
                                             request.vg_buffer.size)

        if request.is_receive() and request.source != consts.MPI_PROC_NULL:
            count = request.datatype.get_count(request.vg_buffer.size)
            if count > request.count:
                e = errormsg.MessageTruncated(self,
                                              message_size=count,
                                              buffer_size=request.count)
                self.add_error_and_throw(e)
            request.datatype.unpack(self.controller,
                                    request.vg_buffer,
                                    count,
                                    request.data_ptr,
                                    check=False)

        if request.is_collective():
            op = self.gstate.get_operation_by_cc_id(request.comm.comm_id,
                                                    request.cc_id)
            op.complete(self)

        self.state.remove_finished_request(request)
