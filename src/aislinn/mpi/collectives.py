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

import types
import copy
import logging
import errormsg
import check
import consts
import comm

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

    def check_compatability(self, op_class, blocking):
        if self.name != op_class.name:
            e = errormsg.CallError()
            e.name = "collectivemismatch"
            e.short_description = "Collective mismatch"
            e.description = "Invalid order of collective operations in " \
                            "communicator {0}. Operation MPI_{1} expected." \
                                .format(comm.comm_id_name(self.comm_id),
                                        self.mpi_name)
            e.throw()

        if self.blocking != blocking:
            e = errormsg.CallError()
            e.name = "blocknonblockcc"
            e.short_description = "Blocking collective mixed with nonblocking"
            e.description = "Blocking collective operation mixed " \
                            "with nonblocking"
            e.throw()

    def copy(self):
        op = copy.copy(self)
        op.after_copy()
        return op

    def after_copy(self):
        pass

    def enter(self, generator, state, comm, args):
        logging.debug("Entering collective operation %s", self)
        assert self.remaining_processes_enter >= 0
        self.remaining_processes_enter -= 1
        self.enter_main(generator, state, comm, args)

    def complete(self, generator, state):
        logging.debug("Completing collective operation %s", self)
        assert self.remaining_processes_complete >= 0
        self.remaining_processes_complete -= 1
        self.complete_main(generator, state, state.get_comm(self.comm_id))
        if self.remaining_processes_complete == 0:
            state.gstate.finish_collective_operation(self)
            self.dispose()

    def is_finished(self):
        return self.remaining_processes_complete == 0

    def has_root(self):
        return self.root is not None

    def check_root(self, comm, root):
        if self.root is None:
            self.root = root
            self.root_pid = comm.group.rank_to_pid(root)
        elif self.root != root:
            e = errormsg.CallError()
            e.name = "rootmismatch"
            e.short_description = "Root mismatch"
            e.description = "Root mismatch"
            e.throw()

    def compute_hash(self, hashthread):
        hashthread.update("{0} {1} {2} {3} {4} {5}".
                format(self.name,
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


class OperationWithBuffers(CollectiveOperation):

    def __init__(self, gstate, comm, blocking, cc_id):
        CollectiveOperation.__init__(self, gstate, comm, blocking, cc_id)
        self.buffers = [ None ] * self.process_count

    def after_copy(self):
        for vg_buffer in self.buffers:
            if vg_buffer:
                vg_buffer.inc_ref()

    def dispose(self):
        for vg_buffer in self.buffers:
            if vg_buffer:
                vg_buffer.dec_ref()

    def compute_hash_data(self, hashthread):
        for vg_buffer in self.buffers:
            if vg_buffer is not None:
                hashthread.update(vg_buffer.hash)
            else:
                hashthread.update("-")


class OperationWithSingleBuffer(CollectiveOperation):

    def __init__(self, gstate, comm, blocking, cc_id):
        CollectiveOperation.__init__(self, gstate, comm, blocking, cc_id)
        self.buffer = None

    def after_copy(self):
        if self.buffer:
            self.buffer.inc_ref()

    def dispose(self):
        if self.buffer:
            self.buffer.dec_ref()

    def compute_hash_data(self, hashthread):
        if self.buffer is not None:
            hashthread.update(self.buffer.hash)
        else:
            hashthread.update("-")


class Barrier(CollectiveOperation):

    name = "barrier"

    def enter_main(self,
                   generator,
                   state,
                   comm,
                   args):
        pass

    def can_be_completed(self, state):
        return self.remaining_processes_enter == 0

    def complete_main(self, generator, state, comm):
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
                   generator,
                   state,
                   comm,
                   args):
        sendbuf, sendcount, sendtype, \
               recvbuf, recvcounts, displs, recvtype, root = args
        check.check_rank(comm, root, 8)
        rank = state.get_rank(comm)
        self.check_root(comm, root)

        assert self.buffers[rank] is None
        self.buffers[rank] = generator.new_buffer_and_pack(
                sendtype, sendcount, sendbuf)

        if root == rank:
            recvtype = check.check_datatype(state, recvtype, 7)
            self.recvtype = recvtype
            self.recvbuf = recvbuf
            self.recvcounts = generator.controller.read_ints(
                    recvcounts, self.process_count)
            self.displs = generator.controller.read_ints(
                    displs, self.process_count)

    def can_be_completed(self, state):
        return state.pid != self.root_pid or \
               self.remaining_processes_enter == 0

    def complete_main(self, generator, state, comm):
        if state.pid == self.root_pid:
            recvbuf = self.recvbuf
            controller = generator.controller
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
        hashthread.update(str(self.recvtype.type_id if self.recvtype else None))
        hashthread.update(str(self.displs))


class Gather(OperationWithBuffers):

    name = "gather"

    def __init__(self, gstate, comm, blocking, cc_id):
        OperationWithBuffers.__init__(self, gstate, comm, blocking, cc_id)
        self.recvbuf = None
        self.recvcount = None
        self.recvtype = None

    def enter_main(self,
                   generator,
                   state,
                   comm,
                   args):
        sendbuf, sendcount, sendtype, \
               recvbuf, recvcount, recvtype, root = args
        check.check_rank(comm, root, 7, False, False)
        self.check_root(comm, root)

        rank = state.get_rank(comm)
        if self.root == rank:
            self.recvbuf = recvbuf
            self.recvtype = check.check_datatype(state, recvtype, 7)
            check.check_count(recvcount, 5)
            self.recvcount = recvcount

        self.sendtype = sendtype
        self.sendcount = sendcount

        assert self.buffers[rank] is None
        self.buffers[rank] = generator.new_buffer_and_pack(
                sendtype, sendcount, sendbuf)

    def can_be_completed(self, state):
        return state.pid != self.root_pid or \
               self.remaining_processes_enter == 0

    def complete_main(self, generator, state, comm):
        if state.pid == self.root_pid:
            controller = generator.controller
            for i, vg_buffer in enumerate(self.buffers):
                self.recvtype.unpack(controller,
                                     vg_buffer,
                                     self.recvcount,
                                     self.recvbuf + i * self.recvtype.size
                                                      * self.recvcount)

    def compute_hash_data(self, hashthread):
        OperationWithBuffers.compute_hash_data(self, hashthread)
        hashthread.update(str(self.recvcount))
        hashthread.update(str(self.recvtype if self.recvtype else None))
        hashthread.update(str(self.recvbuf))


class Scatterv(OperationWithSingleBuffer):

    name = "scatterv"

    def __init__(self, gstate, comm, blocking, cc_id):
        OperationWithSingleBuffer.__init__(self, gstate, comm, blocking, cc_id)
        self.recvbufs = [ None ] * self.process_count
        self.recvcounts = [ None ] * self.process_count
        self.recvtypes = [ None ] * self.process_count
        self.sendtype = None
        self.sendcounts = None
        self.displs = None

    def after_copy(self):
        OperationWithSingleBuffer.after_copy(self)
        self.recvbufs = copy.copy(self.recvbufs)
        self.recvcounts = copy.copy(self.recvcounts)
        self.recvtypes = copy.copy(self.recvtypes)

    def enter_main(self,
                   generator,
                   state,
                   comm,
                   args):
        sendbuf, sendcounts, displs, sendtype, \
               recvbuf, recvcount, recvtype, root = args
        check.check_rank(comm, root, 8)
        self.check_root(comm, root)
        rank = state.get_rank(comm)
        self.recvbufs[rank] = recvbuf
        self.recvtypes[rank] = recvtype
        self.recvcounts[rank] = recvcount
        if self.root == rank:
            sendtype = check.check_datatype(state, sendtype, 4)
            self.sendtype = sendtype
            self.sendcounts = generator.controller.read_ints(
                    sendcounts, self.process_count)
            self.displs = generator.controller.read_ints(
                    displs, self.process_count)
            sendcount = max(s + d for s, d in zip(self.sendcounts, self.displs))
            assert self.buffer is None
            self.buffer = generator.new_buffer_and_pack(sendtype, sendcount, sendbuf)

    def can_be_completed(self, state):
        return self.buffer is not None

    def complete_main(self, generator, state, comm):
        rank = state.get_rank(comm)
        index =  self.sendtype.size * self.displs[rank]
        self.recvtypes[rank].unpack(generator.controller,
                                    self.buffer,
                                    self.recvcounts[rank],
                                    self.recvbufs[rank],
                                    index)

    def compute_hash_data(self, hashthread):
        OperationWithSingleBuffer.compute_hash_data(self, hashthread)
        hashthread.update(str(self.sendcounts))
        hashthread.update(str(self.recvbufs))
        hashthread.update(str(t.type_id if t else None for t in self.recvtypes))
        hashthread.update(str(self.recvcounts))
        hashthread.update(str(self.displs))
        hashthread.update(str(self.sendcounts))
        hashthread.update(str(self.sendtype.type_id if self.sendtype else None))


class Scatter(OperationWithSingleBuffer):

    name = "scatter"

    def __init__(self, gstate, comm, blocking, cc_id):
        OperationWithSingleBuffer.__init__(self, gstate, comm, blocking, cc_id)
        self.sendtype = None
        self.sendcount = None
        self.recvbufs = [ None ] * self.process_count
        self.recvcounts = [ None ] * self.process_count
        self.recvtypes = [ None ] * self.process_count

    def after_copy(self):
        OperationWithSingleBuffer.after_copy(self)
        self.recvbufs = copy.copy(self.recvbufs)
        self.recvcounts = copy.copy(self.recvcounts)
        self.recvtypes = copy.copy(self.recvtypes)

    def enter_main(self,
                   generator,
                   state,
                   comm,
                   args):
        sendbuf, sendcount, sendtype, \
               recvbuf, recvcount, recvtype, root = args
        check.check_rank(comm, root, 8)
        self.check_root(comm, root)
        rank = state.get_rank(comm)
        self.recvbufs[rank] = recvbuf
        self.recvtypes[rank] = recvtype
        self.recvcounts[rank] = recvcount
        if self.root == rank:
            check.check_count(sendcount, 2)
            sendtype = check.check_datatype(state, sendtype, 3)
            self.sendtype = sendtype
            self.sendcount = sendcount
            assert self.buffer is None
            self.buffer = generator.new_buffer_and_pack(
                    sendtype, sendcount * self.process_count, sendbuf)

    def can_be_completed(self, state):
        return self.buffer is not None

    def complete_main(self, generator, state, comm):
        rank = state.get_rank(comm)
        index = rank * self.sendtype.size * self.sendcount
        self.recvtypes[rank].unpack(generator.controller,
                                    self.buffer,
                                    self.recvcounts[rank],
                                    self.recvbufs[rank],
                                    index)

    def compute_hash_data(self, hashthread):
        OperationWithSingleBuffer.compute_hash_data(self, hashthread)
        hashthread.update(str(self.sendtype.type_id if self.sendtype else None))
        hashthread.update(str(self.sendcount))
        hashthread.update(str(self.recvbufs))
        hashthread.update(str(t.type_id if t else None for t in self.recvtypes))
        hashthread.update(str(self.recvcounts))

class Bcast(OperationWithSingleBuffer):

    name = "bcast"

    def __init__(self, gstate, comm, blocking, cc_id):
        OperationWithSingleBuffer.__init__(self, gstate, comm, blocking, cc_id)
        self.recvbufs = [ None ] * self.process_count
        self.counts = [ None ] * self.process_count
        self.datatypes = [ None ] * self.process_count
        self.root = None

    def after_copy(self):
        OperationWithSingleBuffer.after_copy(self)
        self.recvbufs = copy.copy(self.recvbufs)
        self.recvcounts = copy.copy(self.counts)
        self.recvtypes = copy.copy(self.types)

    def enter_main(self,
                   generator,
                   state,
                   comm,
                   args):
        buffer, count, datatype, root = args
        check.check_rank(comm, root, 8)
        self.check_root(comm, root)
        rank = state.get_rank(comm)
        if self.root == rank:
            self.count = count
            assert self.buffer is None
            self.buffer = generator.new_buffer_and_pack(datatype, count, buffer)
        else:
            self.recvbufs[rank] = buffer
            self.datatypes[rank] = datatype
            self.counts[rank] = count

    def can_be_completed(self, state):
        return self.buffer is not None

    def complete_main(self, generator, state, comm):
        rank = state.get_rank(comm)
        if self.root != rank:
            self.datatypes[rank].unpack(generator.controller,
                                        self.buffer,
                                        self.counts[rank],
                                        self.recvbufs[rank])

    def compute_hash_data(self, hashthread):
        OperationWithSingleBuffer.compute_hash_data(self, hashthread)
        hashthread.update(str(self.recvbufs))
        hashthread.update(str(self.counts))
        hashthread.update(str([t.type_id if t else None
                               for t in self.datatypes]))


class Reduce(OperationWithBuffers):

    name = "reduce"

    def __init__(self, gstate, comm, blocking, cc_id):
        OperationWithBuffers.__init__(self, gstate, comm, blocking, cc_id)
        self.recvbuf = None
        self.datatype = None
        self.count = None
        self.op = None

    def enter_main(self,
                   generator,
                   state,
                   comm,
                   args):

        sendbuf, recvbuf, count, datatype, op, root = args
        check.check_rank(comm, root, 6)

        if self.op is None:
            self.op = op
            self.count = count
            self.datatype = datatype
        else:
            assert (self.op == op and
                    self.count == count and
                    self.datatype == datatype)

        self.check_root(comm, root)

        rank = state.get_rank(comm)
        if self.root == rank:
            generator.controller.memcpy(recvbuf, sendbuf, datatype.size * count)
        else:
            self.recvbuf = recvbuf
            assert self.buffers[rank] is None
            self.buffers[rank] = generator.new_buffer_and_pack(datatype,
                                                               count,
                                                               sendbuf)

    def can_be_completed(self, state):
        return state.pid != self.root_pid or \
               self.remaining_processes_enter == 0

    def complete_main(self, generator, state, comm):
        if state.pid == self.root_pid:
            vg_datatype, vg_op = types.translate_reduction_op(self.datatype,
                                                              self.op)
            rank = state.get_rank(comm)
            for r in xrange(self.process_count):
                if r == rank:
                    continue
                generator.controller.reduce(self.recvbuf,
                                            vg_datatype,
                                            self.count,
                                            vg_op,
                                            self.buffers[r].id)

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
        self.recvbufs = [ None ] * self.process_count
        self.datatype = None
        self.count = None
        self.op = None

    def after_copy(self):
        OperationWithBuffers.after_copy(self)
        self.recvbufs = copy.copy(self.recvbufs)

    def enter_main(self,
                   generator,
                   state,
                   comm,
                   args):

        sendbuf, recvbuf, count, datatype, op = args

        if self.op is None:
            self.op = op
            self.count = count
            self.datatype = datatype
        else:
            assert (self.op == op and
                    self.count == count and
                    self.datatype == datatype)

        generator.controller.memcpy(recvbuf, sendbuf, datatype.size * count)
        rank = state.get_rank(comm)
        self.recvbufs[rank] = recvbuf
        assert self.buffers[rank] is None
        self.buffers[rank] = generator.new_buffer_and_pack(
                datatype, count, sendbuf)

    def can_be_completed(self, state):
        return self.remaining_processes_enter == 0

    def complete_main(self, generator, state, comm):
        vg_datatype, vg_op = types.translate_reduction_op(self.datatype,
                                                          self.op)
        rank = state.get_rank(comm)
        recvbuf = self.recvbufs[rank]
        for r in xrange(self.process_count):
            if rank == r:
                continue
            generator.controller.reduce(recvbuf,
                                        vg_datatype,
                                        self.count,
                                        vg_op,
                                        self.buffers[r].id)

    def compute_hash_data(self, hashthread):
        OperationWithBuffers.compute_hash_data(self, hashthread)
        hashthread.update(str(self.recvbufs))
        hashthread.update(str(self.datatype.type_id))
        hashthread.update(str(self.count))
        hashthread.update(str(self.op))


class CommSplit(CollectiveOperation):

    name = "comm_split"

    def __init__(self, gstate, comm, blocking, cc_id):
        CollectiveOperation.__init__(self, gstate, comm, blocking, cc_id)
        self.colors = [ None ] * self.process_count
        self.keys = [ None ] * self.process_count
        self.newcomm_ptrs = [ None ] * self.process_count
        self.comm_ids = [ None ] * self.process_count

    def after_copy(self):
        self.colors = copy.copy(self.colors)
        self.keys = copy.copy(self.keys)
        self.newcomm_ptrs = copy.copy(self.newcomm_ptrs)
        self.comm_ids = copy.copy(self.comm_ids)

    def enter_main(self,
                   generator,
                   state,
                   comm,
                   args):
        color, key, newcomm_ptr = args
        # In comm_id is first argument, but is was removed from args
        check.check_color(color, 2)
        rank = state.get_rank(comm)

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
                    groups[color] = [ (key, r) ]
                else:
                    g.append((key, r))
            items = groups.items()
            items.sort() # Make it more deterministic
            for color, g in items:
                g.sort() # This sort is needed by MPI specification
                ranks = [ r for key, r in g ]
                c = state.gstate.create_new_communicator(comm, ranks)
                for r in ranks:
                    self.comm_ids[r] = c.comm_id
            self.colors = None
            self.keys = None

    def can_be_completed(self, state):
        return self.remaining_processes_enter == 0

    def complete_main(self, generator, state, comm):
        rank = state.get_rank(comm)
        comm_id = self.comm_ids[rank]
        if comm_id is None:
            comm_id = consts.MPI_COMM_NULL
        generator.controller.write_int(self.newcomm_ptrs[rank],
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
        self.newcomm_ptrs = [ None ] * self.process_count
        self.newcomm_id = None

    def after_copy(self):
        self.newcomm_ptrs = copy.copy(self.newcomm_ptrs)

    def enter_main(self,
                   generator,
                   state,
                   comm,
                   args):
        newcomm_ptr = args
        rank = state.get_rank(comm)

        assert self.newcomm_ptrs[rank] is None
        self.newcomm_ptrs[rank] = newcomm_ptr

        if self.newcomm_id is None:
            self.newcomm_id = state.gstate.clone_communicator(comm).comm_id

    def can_be_completed(self, state):
        return True

    def complete_main(self, generator, state, comm):
        rank = state.get_rank(comm)
        generator.controller.write_int(self.newcomm_ptrs[rank],
                                       self.newcomm_id)

    def compute_hash_data(self, hashthread):
        hashthread.update(str(self.newcomm_ptrs))
        hashthread.update(str(self.newcomm_id))
