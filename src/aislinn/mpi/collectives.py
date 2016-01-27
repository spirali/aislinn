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

import copy
import logging
import errormsg
import check
import consts


class CollectiveOperation:

    def __init__(self, gstate, comm, blocking, cc_id):
        self.cc_id = cc_id
        self.comm_id = comm.comm_id
        self.blocking = blocking
        self.root = None
        self.root_pid = None
        self.process_count = comm.group.size
        self.remaining_processes_enter = self.process_count
        self.remaining_processes_complete = self.process_count
        self.data = None
        logging.debug("New collective operation %s", self)

    def check_compatability(self, context, op_class, blocking):
        if self.name != op_class.name:
            e = errormsg.CollectiveMixing(context)
            context.add_error_and_throw(e)

        if self.blocking != blocking:
            e = errormsg.CollectiveMixingBlockingNonBlocking(context)
            context.add_error_and_throw(e)

    def copy(self):
        op = copy.copy(self)
        op.after_copy()
        return op

    def after_copy(self):
        pass

    def transfer(self, transfer_context):
        return self.copy()

    def enter(self, context, comm, args):
        logging.debug("Entering collective operation %s", self)
        assert self.remaining_processes_enter > 0
        assert self.remaining_processes_complete >= 0
        self.remaining_processes_enter -= 1
        self.enter_main(context, comm, args)

    def complete(self, context):
        logging.debug("Completing collective operation %s", self)
        assert self.remaining_processes_complete >= 0
        self.remaining_processes_complete -= 1
        self.complete_main(context, context.state.get_comm(self.comm_id))
        if self.remaining_processes_complete == 0:
            context.gstate.finish_collective_operation(self)
            self.dispose()

    def is_finished(self):
        return self.remaining_processes_complete == 0

    def has_root(self):
        return self.root is not None

    def check_root(self, context, comm, root):
        if self.root is None:
            self.root = root
            self.root_pid = comm.group.rank_to_pid(root)
        elif self.root != root:
            context.add_error_and_throw(
                errormsg.RootMismatch(context, value1=self.root, value2=root))

    def compute_hash(self, hashthread):
        hashthread.update(
            "{0} {1} {2} {3} {4} {5}".format(
                self.name,
                self.comm_id,
                self.blocking,
                self.root,
                self.remaining_processes_complete,
                self.remaining_processes_enter))
        self.compute_hash_data(hashthread)

    @property
    def mpi_name(self):
        if not self.blocking:
            return "I" + self.name
        else:
            return self.name.capitalize()

    def dispose(self):
        pass

    def __repr__(self):
        return "<{0} {1:x} cc_id={2} renter={3} rcomplete={4}>" \
               .format(self.name,
                       id(self),
                       self.cc_id,
                       self.remaining_processes_enter,
                       self.remaining_processes_complete)

    def sanity_check(self):
        pass


class OperationWithBuffers(CollectiveOperation):

    def __init__(self, gstate, comm, blocking, cc_id):
        CollectiveOperation.__init__(self, gstate, comm, blocking, cc_id)
        self.buffers = [None] * self.process_count

    def copy(self):
        op = CollectiveOperation.copy(self)
        op.buffers = copy.copy(self.buffers)
        for vg_buffer in self.buffers:
            if vg_buffer:
                vg_buffer.inc_ref()
        return op

    def transfer(self, transfer_context):
        op = copy.copy(self)
        op.buffers = [transfer_context.transfer_buffer(vg_buffer)
                      if vg_buffer else None
                      for vg_buffer in self.buffers]
        return op

    def dispose(self):
        for vg_buffer in self.buffers:
            if vg_buffer:
                vg_buffer.dec_ref()

    def compute_hash_data(self, hashthread):
        for vg_buffer in self.buffers:
            if vg_buffer:
                hashthread.update(vg_buffer.hash)

    def sanity_check(self):
        CollectiveOperation.sanity_check(self)
        for vg_buffer in self.buffers:
            assert vg_buffer is None or vg_buffer.ref_count > 0, \
                "Zero reference in " + repr(vg_buffer)

    def make_buffer_for_all(
            self, context, rank, comm, pointer, datatype, count):
        assert self.buffers[rank] is None
        self.buffers[rank] = context.make_buffer_for_more(
            comm.group.pids(), pointer, datatype, count)

    def make_buffer_for_root(
            self, context, rank, comm, pointer, datatype, count):
        assert self.buffers[rank] is None
        self.buffers[rank] = context.make_buffer_for_one(
            self.root_pid, pointer, datatype, count)


class Barrier(CollectiveOperation):

    name = "barrier"

    def enter_main(self,
                   context,
                   comm,
                   args):
        pass

    def can_be_completed(self, state):
        return self.remaining_processes_enter == 0

    def complete_main(self, context, comm):
        pass

    def compute_hash_data(self, hashthread):
        pass


class Gatherv(OperationWithBuffers):

    name = "gatherv"

    def __init__(self, gstate, comm, blocking, cc_id):
        OperationWithBuffers.__init__(self, gstate, comm, blocking, cc_id)
        self.sendtype = None
        self.recvbuf = None
        self.recvcounts = None
        self.recvtype = None
        self.displs = None

    def enter_main(self,
                   context,
                   comm,
                   args):
        sendbuf, sendcount, sendtype, \
            recvbuf, recvcounts, displs, recvtype, root = args
        check.check_rank(context, comm, root, 8)
        rank = context.state.get_rank(comm)
        self.check_root(context, comm, root)

        self.make_buffer_for_root(
            context, rank, comm, sendbuf, sendtype, sendcount)

        if root == rank:
            recvtype = check.check_datatype(context, recvtype, 7)
            self.recvtype = recvtype
            self.recvbuf = recvbuf
            self.recvcounts = context.controller.read_ints(recvcounts,
                                                           self.process_count)
            self.displs = context.controller.read_ints(displs,
                                                       self.process_count)

    def can_be_completed(self, state):
        return state.pid != self.root_pid or \
            self.remaining_processes_enter == 0

    def complete_main(self, context, comm):
        if context.state.pid == self.root_pid:
            recvbuf = self.recvbuf
            controller = context.controller
            for vg_buffer, count, displ in zip(self.buffers,
                                               self.recvcounts,
                                               self.displs):
                self.recvtype.unpack(controller,
                                     vg_buffer,
                                     count,
                                     recvbuf + displ * self.recvtype.size)
        # Do nothing on non-root processes

    def compute_hash_data(self, hashthread):
        OperationWithBuffers.compute_hash_data(self, hashthread)
        hashthread.update(str(self.recvbuf))
        hashthread.update(str(self.recvtype.type_id
                          if self.recvtype else None))
        hashthread.update(str(self.displs))


class Gather(OperationWithBuffers):

    name = "gather"

    def __init__(self, gstate, comm, blocking, cc_id):
        OperationWithBuffers.__init__(self, gstate, comm, blocking, cc_id)
        self.recvbuf = None
        self.recvcount = None
        self.recvtype = None

    def enter_main(self,
                   context,
                   comm,
                   args):
        sendbuf, sendcount, sendtype, \
            recvbuf, recvcount, recvtype, root = args
        check.check_rank(context, comm, root, 7, False, False)
        self.check_root(context, comm, root)

        rank = context.state.get_rank(comm)
        if self.root == rank:
            self.recvbuf = recvbuf
            self.recvtype = check.check_datatype(context, recvtype, 7)
            check.check_count(context, recvcount, 5)
            self.recvcount = recvcount

        self.sendtype = sendtype
        self.sendcount = sendcount

        assert self.buffers[rank] is None

        if sendbuf == consts.MPI_IN_PLACE:
            if rank != root:
                context.add_error_and_throw(errormsg.InvalidInPlace(context))
        else:
            self.make_buffer_for_root(
                context, rank, comm, sendbuf, sendtype, sendcount)

    def can_be_completed(self, state):
        return state.pid != self.root_pid or \
            self.remaining_processes_enter == 0

    def complete_main(self, context, comm):
        if context.state.pid == self.root_pid:
            controller = context.controller
            for i, vg_buffer in enumerate(self.buffers):
                if vg_buffer:  # if vg_buffer is None, MPI_IN_PLACE was used
                    self.recvtype.unpack(controller,
                                         vg_buffer,
                                         self.recvcount,
                                         self.recvbuf + i * self.recvtype.size
                                                          * self.recvcount)

    def compute_hash_data(self, hashthread):
        OperationWithBuffers.compute_hash_data(self, hashthread)
        hashthread.update(str(self.recvcount))
        hashthread.update(str(self.recvtype.type_id
                          if self.recvtype else None))
        hashthread.update(str(self.recvbuf))


class Allgather(OperationWithBuffers):

    name = "allgather"

    def __init__(self, gstate, comm, blocking, cc_id):
        OperationWithBuffers.__init__(self, gstate, comm, blocking, cc_id)
        self.recvbufs = [None] * self.process_count
        self.recvcounts = [None] * self.process_count
        self.recvtypes = [None] * self.process_count

    def enter_main(self,
                   context,
                   comm,
                   args):
        sendbuf, sendcount, sendtype, \
            recvbuf, recvcount, recvtype = args

        rank = context.state.get_rank(comm)
        self.recvbufs[rank] = recvbuf
        self.recvtypes[rank] = check.check_datatype(context, recvtype, 7)
        check.check_count(context, recvcount, 5)
        self.recvcounts[rank] = recvcount
        self.make_buffer_for_all(
            context, rank, comm, sendbuf, sendtype, sendcount)

    def can_be_completed(self, state):
        return self.remaining_processes_enter == 0

    def complete_main(self, context, comm):
        rank = context.state.get_rank(comm)
        controller = context.controller
        for i, vg_buffer in enumerate(self.buffers):
            self.recvtypes[rank].unpack(
                controller,
                vg_buffer,
                self.recvcounts[rank],
                self.recvbufs[rank] + i * self.recvtypes[rank].size
                * self.recvcounts[rank])

    def compute_hash_data(self, hashthread):
        OperationWithBuffers.compute_hash_data(self, hashthread)
        hashthread.update(str(self.recvcounts))
        # FIXME: hash self.recvtypes
        hashthread.update(str(self.recvbufs))


class Allgatherv(OperationWithBuffers):

    name = "allgatherv"

    def __init__(self, gstate, comm, blocking, cc_id):
        OperationWithBuffers.__init__(self, gstate, comm, blocking, cc_id)
        self.recvbufs = [None] * self.process_count
        self.recvcounts = [None] * self.process_count
        self.recvtypes = [None] * self.process_count
        self.displs = [None] * self.process_count

    def enter_main(self,
                   context,
                   comm,
                   args):
        sendbuf, sendcount, sendtype, \
            recvbuf, recvcounts, displs, recvtype = args
        rank = context.state.get_rank(comm)
        assert self.buffers[rank] is None
        self.make_buffer_for_all(
            context, rank, comm, sendbuf, sendtype, sendcount)
        recvtype = check.check_datatype(context, recvtype, 7)
        self.recvtypes[rank] = recvtype
        self.recvbufs[rank] = recvbuf
        self.recvcounts[rank] = context.controller.read_ints(
            recvcounts, self.process_count)
        self.displs[rank] = context.controller.read_ints(
            displs, self.process_count)

    def can_be_completed(self, state):
        return self.remaining_processes_enter == 0

    def complete_main(self, context, comm):
        rank = context.state.get_rank(comm)
        controller = context.controller
        recvbuf = self.recvbufs[rank]
        recvtype = self.recvtypes[rank]
        for vg_buffer, count, displ in zip(self.buffers,
                                           self.recvcounts[rank],
                                           self.displs[rank]):
            recvtype.unpack(controller,
                            vg_buffer,
                            count,
                            recvbuf + displ * recvtype.size)

    def compute_hash_data(self, hashthread):
        OperationWithBuffers.compute_hash_data(self, hashthread)
        hashthread.update(str(self.recvbufs))
        hashthread.update(str(self.recvtypes))
        hashthread.update(str(self.displs))


class Scatterv(OperationWithBuffers):

    name = "scatterv"

    def __init__(self, gstate, comm, blocking, cc_id):
        OperationWithBuffers.__init__(self, gstate, comm, blocking, cc_id)
        self.recvbufs = [None] * self.process_count
        self.recvcounts = [None] * self.process_count
        self.recvtypes = [None] * self.process_count
        self.sendtype = None
        self.sendcounts = None
        self.displs = None

    def after_copy(self):
        OperationWithBuffers.after_copy(self)
        self.recvbufs = copy.copy(self.recvbufs)
        self.recvcounts = copy.copy(self.recvcounts)
        self.recvtypes = copy.copy(self.recvtypes)

    def enter_main(self,
                   context,
                   comm,
                   args):
        sendbuf, sendcounts, displs, sendtype, \
            recvbuf, recvcount, recvtype, root = args
        check.check_rank(context, comm, root, 8)
        self.check_root(context, comm, root)
        rank = context.state.get_rank(comm)
        self.recvbufs[rank] = recvbuf
        self.recvtypes[rank] = recvtype
        self.recvcounts[rank] = recvcount
        if self.root == rank:
            sendtype = check.check_datatype(context, sendtype, 4)
            self.sendtype = sendtype
            self.sendcounts = context.controller.read_ints(
                sendcounts, self.process_count)
            self.displs = context.controller.read_ints(
                displs, self.process_count)
            sendcount = max(s + d
                            for s, d in zip(self.sendcounts, self.displs))
            self.make_buffer_for_all(
                context, rank, comm, sendbuf, sendtype, sendcount)

    def can_be_completed(self, state):
        return self.buffers[self.root] is not None

    def complete_main(self, context, comm):
        rank = context.state.get_rank(comm)
        index = self.sendtype.size * self.displs[rank]
        self.recvtypes[rank].unpack(context.controller,
                                    self.buffers[self.root],
                                    self.recvcounts[rank],
                                    self.recvbufs[rank],
                                    index)

    def compute_hash_data(self, hashthread):
        OperationWithBuffers.compute_hash_data(self, hashthread)
        hashthread.update(str(self.sendcounts))
        hashthread.update(str(self.recvbufs))
        hashthread.update(str(t.type_id if t else None
                              for t in self.recvtypes))
        hashthread.update(str(self.recvcounts))
        hashthread.update(str(self.displs))
        hashthread.update(str(self.sendcounts))
        hashthread.update(str(self.sendtype.type_id
                              if self.sendtype else None))


class Scatter(OperationWithBuffers):

    name = "scatter"

    def __init__(self, gstate, comm, blocking, cc_id):
        OperationWithBuffers.__init__(self, gstate, comm, blocking, cc_id)
        self.sendtype = None
        self.sendcount = None
        self.recvbufs = [None] * self.process_count
        self.recvcounts = [None] * self.process_count
        self.recvtypes = [None] * self.process_count

    def after_copy(self):
        OperationWithBuffers.after_copy(self)
        self.recvbufs = copy.copy(self.recvbufs)
        self.recvcounts = copy.copy(self.recvcounts)
        self.recvtypes = copy.copy(self.recvtypes)

    def enter_main(self,
                   context,
                   comm,
                   args):
        sendbuf, sendcount, sendtype, \
            recvbuf, recvcount, recvtype, root = args
        check.check_rank(context, comm, root, 8)
        self.check_root(context, comm, root)
        rank = context.state.get_rank(comm)
        self.recvbufs[rank] = recvbuf
        self.recvtypes[rank] = recvtype
        self.recvcounts[rank] = recvcount

        if self.root == rank:
            check.check_count(context, sendcount, 2)
            sendtype = check.check_datatype(context, sendtype, 3)
            self.sendtype = sendtype
            self.sendcount = sendcount
            self.make_buffer_for_all(
                context, rank, comm, sendbuf,
                sendtype, sendcount * self.process_count)
        elif recvbuf == consts.MPI_IN_PLACE:
            context.add_error_and_throw(errormsg.InvalidInPlace(context))

    def can_be_completed(self, state):
        return self.buffers[self.root] is not None

    def complete_main(self, context, comm):
        rank = context.state.get_rank(comm)
        index = rank * self.sendtype.size * self.sendcount
        recvbuf = self.recvbufs[rank]
        if recvbuf != consts.MPI_IN_PLACE:
            self.recvtypes[rank].unpack(context.controller,
                                        self.buffers[self.root],
                                        self.recvcounts[rank],
                                        self.recvbufs[rank],
                                        index)

    def compute_hash_data(self, hashthread):
        OperationWithBuffers.compute_hash_data(self, hashthread)
        hashthread.update(str(self.sendtype.type_id
                              if self.sendtype else None))
        hashthread.update(str(self.sendcount))
        hashthread.update(str(self.recvbufs))
        hashthread.update(str(t.type_id if t else None
                              for t in self.recvtypes))
        hashthread.update(str(self.recvcounts))


class Bcast(OperationWithBuffers):

    name = "bcast"

    def __init__(self, gstate, comm, blocking, cc_id):
        OperationWithBuffers.__init__(self, gstate, comm, blocking, cc_id)
        self.recvbufs = [None] * self.process_count
        self.counts = [None] * self.process_count
        self.datatypes = [None] * self.process_count
        self.root = None

    def after_copy(self):
        OperationWithBuffers.after_copy(self)
        self.recvbufs = copy.copy(self.recvbufs)
        self.counts = copy.copy(self.counts)
        self.datatypes = copy.copy(self.datatypes)

    def enter_main(self,
                   context,
                   comm,
                   args):
        buffer, count, datatype, root = args
        check.check_rank(context, comm, root, 8)
        self.check_root(context, comm, root)
        rank = context.state.get_rank(comm)
        if self.root == rank:
            self.count = count
            self.make_buffer_for_all(
                context, rank, comm, buffer, datatype, count)
        else:
            self.recvbufs[rank] = buffer
            self.datatypes[rank] = datatype
            self.counts[rank] = count

    def can_be_completed(self, state):
        return self.buffers[self.root] is not None

    def complete_main(self, context, comm):
        rank = context.state.get_rank(comm)
        if self.root != rank:
            self.datatypes[rank].unpack(context.controller,
                                        self.buffers[self.root],
                                        self.counts[rank],
                                        self.recvbufs[rank])

    def compute_hash_data(self, hashthread):
        OperationWithBuffers.compute_hash_data(self, hashthread)
        hashthread.update(str(self.recvbufs))
        hashthread.update(str(self.counts))
        hashthread.update(str([t.type_id if t else None
                               for t in self.datatypes]))


def execute_reduce_op(context, comm, rank, ccop,
                      recvbuf, buffers, count, scan=False):
    controller = context.controller
    # We have to use malloc because operation runs in client context
    # and buffers are not visible for code in client
    tmp = controller.client_malloc(controller.INT_SIZE * 2)
    len_ptr = tmp
    datatype_ptr = tmp + controller.INT_SIZE
    controller.write_int(len_ptr, count)
    controller.write_int(datatype_ptr, ccop.datatype.type_id)
    controller.write_buffer(recvbuf, buffers[0].id)

    if scan:
        limit = rank + 1
    else:
        limit = ccop.process_count

    for r in xrange(1, limit):
        buffer_mem = controller.client_malloc_from_buffer(buffers[r].id)
        context.run_function(
            ccop.op.fn_ptr,
            controller.FUNCTION_4_POINTER,
            buffer_mem, recvbuf, len_ptr, datatype_ptr)
        controller.client_free(buffer_mem)
    controller.client_free(tmp)


class Reduce(OperationWithBuffers):

    name = "reduce"

    def __init__(self, gstate, comm, blocking, cc_id):
        OperationWithBuffers.__init__(self, gstate, comm, blocking, cc_id)
        self.recvbuf = None
        self.datatype = None
        self.count = None
        self.op = None

    def enter_main(self,
                   context,
                   comm,
                   args):

        sendbuf, recvbuf, count, datatype, op, root = args
        check.check_rank(context, comm, root, 6)

        if self.op is None:
            self.op = op
            self.count = count
            self.datatype = datatype
        else:
            assert (self.op.fn_ptr == op.fn_ptr and
                    self.count == count and
                    self.datatype == datatype)

        self.check_root(context, comm, root)

        rank = context.state.get_rank(comm)
        self.recvbuf = recvbuf
        assert self.buffers[rank] is None
        self.make_buffer_for_root(
            context, rank, comm, sendbuf, datatype, count)

    def can_be_completed(self, state):
        return state.pid != self.root_pid or \
            self.remaining_processes_enter == 0

    def complete_main(self, context, comm):
        if context.state.pid == self.root_pid:
            rank = context.state.get_rank(comm)
            execute_reduce_op(context, comm, rank,
                              self, self.recvbuf, self.buffers, self.count)

    def compute_hash_data(self, hashthread):
        OperationWithBuffers.compute_hash_data(self, hashthread)
        hashthread.update(str(self.recvbuf))
        hashthread.update(str(self.datatype))
        hashthread.update(str(self.count))
        hashthread.update(str(self.op))


class AllReduce(OperationWithBuffers):

    name = "allreduce"

    def __init__(self, gstate, comm, blocking, cc_id):
        OperationWithBuffers.__init__(self, gstate, comm, blocking, cc_id)
        self.recvbufs = [None] * self.process_count
        self.datatype = None
        self.count = None
        self.op = None

    def after_copy(self):
        OperationWithBuffers.after_copy(self)
        self.recvbufs = copy.copy(self.recvbufs)

    def enter_main(self,
                   context,
                   comm,
                   args):

        sendbuf, recvbuf, count, datatype, op = args

        if self.op is None:
            self.op = op
            self.count = count
            self.datatype = datatype
        else:
            assert (self.op.fn_ptr == self.op.fn_ptr and
                    self.count == count and
                    self.datatype == datatype)

        context.controller.memcpy(recvbuf, sendbuf, datatype.size * count)
        rank = context.state.get_rank(comm)
        self.recvbufs[rank] = recvbuf
        assert self.buffers[rank] is None
        self.make_buffer_for_all(
            context, rank, comm, sendbuf, datatype, count)

    def can_be_completed(self, state):
        return self.remaining_processes_enter == 0

    def complete_main(self, context, comm):
        rank = context.state.get_rank(comm)
        execute_reduce_op(context, comm, rank,
                          self, self.recvbufs[rank], self.buffers, self.count)

    def compute_hash_data(self, hashthread):
        OperationWithBuffers.compute_hash_data(self, hashthread)
        hashthread.update(str(self.recvbufs))
        hashthread.update(str(self.datatype.type_id))
        hashthread.update(str(self.count))
        hashthread.update(str(self.op))


class ReduceScatter(OperationWithBuffers):

    name = "reduce_scatter"

    def __init__(self, gstate, comm, blocking, cc_id):
        OperationWithBuffers.__init__(self, gstate, comm, blocking, cc_id)
        self.recvbufs = [None] * self.process_count
        self.datatype = None
        self.counts = None
        self.op = None
        self.final_buffer = None

    def after_copy(self):
        OperationWithBuffers.after_copy(self)
        self.recvbufs = copy.copy(self.recvbufs)
        if self.final_buffer:
            self.final_buffer.inc_ref()

    def enter_main(self,
                   context,
                   comm,
                   args):

        sendbuf, recvbuf, counts_ptr, datatype, op = args

        counts = context.controller.read_ints(counts_ptr, comm.group.size)

        if self.counts is None:
            self.counts = counts
        elif self.counts != counts:
            context.add_error_and_throw(
                errormsg.CountMismatch(
                    context, value1=self.counts, value2=counts))

        total_count = sum(counts)

        if self.op is None:
            self.op = op
            self.datatype = datatype
        else:
            assert (self.op.fn_ptr == self.op.fn_ptr and
                    self.datatype == datatype)

        rank = context.state.get_rank(comm)
        self.recvbufs[rank] = recvbuf
        self.make_buffer_for_all(
            context, rank, comm, sendbuf, datatype, total_count)
        if self.remaining_processes_enter == 0:
            context.controller.make_buffers()
            tmp = context.controller.client_malloc(
                self.datatype.size * total_count)
            execute_reduce_op(context, comm, rank,
                              self, tmp, self.buffers, total_count)
            self.final_buffer = context.make_buffer_for_more(
                comm.group.pids(), tmp, datatype, total_count)
            context.controller.client_free(tmp)
            for b in self.buffers:
                b.dec_ref()
            self.buffers = []

    def can_be_completed(self, state):
        return self.remaining_processes_enter == 0

    def complete_main(self, context, comm):
        rank = context.state.get_rank(comm)
        count = self.counts[rank]
        index = sum(self.counts[:rank]) * self.datatype.size
        self.datatype.unpack(context.controller,
                             self.final_buffer,
                             count,
                             self.recvbufs[rank],
                             index)

    def compute_hash_data(self, hashthread):
        OperationWithBuffers.compute_hash_data(self, hashthread)
        hashthread.update(str(self.recvbufs))
        hashthread.update(str(self.datatype.type_id))
        hashthread.update(str(self.counts))
        hashthread.update(str(self.op))

    def dispose(self):
        OperationWithBuffers.dispose(self)
        if self.final_buffer:
            self.final_buffer.dec_ref()


class Scan(AllReduce):

    name = "scan"

    def complete_main(self, context, comm):
        rank = context.state.get_rank(comm)
        execute_reduce_op(context, comm, rank,
                          self, self.recvbufs[rank],
                          self.buffers, self.count, scan=True)


class CommSplit(CollectiveOperation):

    name = "comm_split"

    def __init__(self, gstate, comm, blocking, cc_id):
        CollectiveOperation.__init__(self, gstate, comm, blocking, cc_id)
        self.colors = [None] * self.process_count
        self.keys = [None] * self.process_count
        self.newcomm_ptrs = [None] * self.process_count
        self.comm_ids = [None] * self.process_count

    def after_copy(self):
        self.colors = copy.copy(self.colors)
        self.keys = copy.copy(self.keys)
        self.newcomm_ptrs = copy.copy(self.newcomm_ptrs)
        self.comm_ids = copy.copy(self.comm_ids)

    def enter_main(self,
                   context,
                   comm,
                   args):
        color, key, newcomm_ptr = args
        # In comm_id is the first argument, but is was removed from args
        # therefore real position of color is 2
        check.check_color(context, color, 2)
        rank = context.state.get_rank(comm)

        assert self.colors[rank] is None
        assert self.keys[rank] is None

        self.colors[rank] = color
        self.keys[rank] = key
        self.newcomm_ptrs[rank] = newcomm_ptr
        if self.remaining_processes_enter == 0:
            groups = {}
            for (r, (color, key)) in enumerate(zip(self.colors, self.keys)):
                if color == consts.MPI_UNDEFINED:
                    continue
                g = groups.get(color)
                if g is None:
                    groups[color] = [(key, r)]
                else:
                    g.append((key, r))
            items = groups.items()
            items.sort()  # Make it more deterministic
            for color, g in items:
                g.sort()  # This sort is needed by MPI specification
                ranks = [r for key, r in g]
                c = context.gstate.create_new_communicator(comm, ranks)
                for r in ranks:
                    self.comm_ids[r] = c.comm_id
            self.colors = None
            self.keys = None

    def can_be_completed(self, state):
        return self.remaining_processes_enter == 0

    def complete_main(self, context, comm):
        rank = context.state.get_rank(comm)
        comm_id = self.comm_ids[rank]
        if comm_id is None:
            comm_id = consts.MPI_COMM_NULL
        context.controller.write_int(self.newcomm_ptrs[rank],
                                     comm_id)

    def compute_hash_data(self, hashthread):
        hashthread.update(str(self.colors))
        hashthread.update(str(self.keys))
        hashthread.update(str(self.newcomm_ptrs))
        hashthread.update(str(self.comm_ids))


class CommDup(CollectiveOperation):

    name = "comm_dup"

    def __init__(self, gstate, comm, blocking, cc_id):
        CollectiveOperation.__init__(self, gstate, comm, blocking, cc_id)
        self.newcomm_ptrs = [None] * self.process_count
        self.newcomm_id = None

    def after_copy(self):
        self.newcomm_ptrs = copy.copy(self.newcomm_ptrs)

    def enter_main(self,
                   context,
                   comm,
                   args):
        newcomm_ptr = args[0]
        rank = context.state.get_rank(comm)

        assert self.newcomm_ptrs[rank] is None
        self.newcomm_ptrs[rank] = newcomm_ptr

        if self.newcomm_id is None:
            self.newcomm_id = context.gstate.clone_communicator(comm).comm_id
        new_comm = context.state.get_comm(self.newcomm_id)
        context.copy_comm_attrs(comm, new_comm)

    def can_be_completed(self, state):
        return True

    def complete_main(self, context, comm):
        rank = context.state.get_rank(comm)
        context.controller.write_int(self.newcomm_ptrs[rank],
                                     self.newcomm_id)

    def compute_hash_data(self, hashthread):
        hashthread.update(str(self.newcomm_ptrs))
        hashthread.update(str(self.newcomm_id))


class CommCreate(CollectiveOperation):

    name = "comm_create"

    def __init__(self, gstate, comm, blocking, cc_id):
        CollectiveOperation.__init__(self, gstate, comm, blocking, cc_id)
        self.newcomm_ptrs = [None] * self.process_count
        self.group = None
        self.newcomm_id = None

    def after_copy(self):
        self.newcomm_ptrs = copy.copy(self.newcomm_ptrs)

    def enter_main(self,
                   context,
                   comm,
                   args):
        group, newcomm_ptr = args
        if self.group is None:
            self.group = group
        elif self.group != group:
            e = errormsg.GroupMismatch(context)
            context.add_error_and_throw(e)

        rank = context.state.get_rank(comm)
        assert self.newcomm_ptrs[rank] is None
        self.newcomm_ptrs[rank] = newcomm_ptr

        if self.newcomm_id is None:
            self.newcomm_id = context.gstate.create_new_communicator(
                comm, group=group).comm_id

    def can_be_completed(self, state):
        return True

    def complete_main(self, context, comm):
        rank = context.state.get_rank(comm)
        context.controller.write_int(self.newcomm_ptrs[rank],
                                     self.newcomm_id)

    def compute_hash_data(self, hashthread):
        hashthread.update(str(self.newcomm_ptrs))
        hashthread.update(str(self.newcomm_id))
