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
import event


class CollectiveOperation:

    def __init__(self, gstate, blocking, cc_id):
        self.cc_id = cc_id
        self.blocking = blocking
        self.root = None
        self.process_count = gstate.process_count
        self.remaining_processes_enter = self.process_count
        self.remaining_processes_complete = self.process_count
        self.data = None

    def copy(self):
        op = copy.copy(self)
        op.after_copy()
        return op

    def after_copy(self):
        pass

    def enter(self, generator, gstate, state, args):
        logging.debug("Entering collective operation %s", self)
        assert self.remaining_processes_enter >= 0
        self.remaining_processes_enter -= 1
        self.enter_main(generator, gstate, state, args)

    def complete(self, generator, gstate, state):
        logging.debug("Completing collective operation %s", self)
        assert self.remaining_processes_complete >= 0
        self.remaining_processes_complete -= 1
        self.complete_main(generator, gstate, state)
        if self.remaining_processes_complete == 0:
            gstate.finish_collective_operation(self)
            self.dispose()

    def is_finished(self):
        return self.remaining_processes_complete == 0

    def has_root(self):
        return self.root is not None

    def check_root(self, root):
        if self.root is None:
            self.root = root
        elif self.root != root:
            e = errormsg.CallError()
            e.name = "rootmismatch"
            e.short_description = "Root mismatch"
            e.description = "Root mismatch"
            e.throw()

    def compute_hash(self, hashthread):
        hashthread.update("{0} {1} {2} {3} {4}".
                format(self.name,
                       self.blocking,
                       self.root,
                       self.remaining_processes_complete,
                       self.remaining_processes_enter))
        self.compute_hash_data(hashthread)

    def get_event(self, state):
        return event.CollectiveEvent(self.mpi_name, state.rank)

    @property
    def mpi_name(self):
        if not self.blocking:
            return "I" + self.name
        else:
            return self.name.capitalize()

    def __repr__(self):
        return "<{0} {1:x} cc_id={2} renter={3} rcomplete={4}>" \
                    .format(self.name,
                            id(self),
                            self.cc_id,
                            self.remaining_processes_enter,
                            self.remaining_processes_complete)


class OperationWithBuffers(CollectiveOperation):

    def __init__(self, gstate, blocking, cc_id):
        CollectiveOperation.__init__(self, gstate, blocking, cc_id)
        self.buffers = [ None ] * self.remaining_processes_enter

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

    def __init__(self, gstate, blocking, cc_id):
        CollectiveOperation.__init__(self, gstate, blocking, cc_id)
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
                     gstate,
                     state,
                     args):
        pass

    def can_be_completed(self, gstate, state):
        return self.remaining_processes_enter == 0

    def complete_main(self, generator, gstate, state):
        pass

    def compute_hash_data(self, hashthread):
        pass

    def dispose(self):
        pass

class Gatherv(OperationWithBuffers):

    name = "gatherv"

    def __init__(self, gstate, blocking, cc_id):
        OperationWithBuffers.__init__(self, gstate, blocking, cc_id)
        self.sendtype = None
        self.recvbuf = None
        self.sendcounts = [ None ] * self.process_count
        self.recvcounts = None
        self.displs = None

    def enter_main(self,
                     generator,
                     gstate,
                     state,
                     args):
        sendbuf, sendcount, sendtype, \
               recvbuf, recvcounts, displs, recvtype, root, comm = args
        generator.validate_rank(root, 8)
        generator.validate_count(sendcount, 2)
        self.check_root(root)
        if self.root == root:
            self.recvbuf = recvbuf

        self.sendtype = sendtype
        size = types.get_datatype_size(sendtype) * sendcount
        self.sendcounts[state.rank] = sendcount

        assert self.buffers[state.rank] is None
        self.buffers[state.rank] = generator.new_buffer(sendbuf, size)

        if root == state.rank:
            self.recvcounts = generator.controller.read_ints(
                    recvcounts, self.process_count)
            self.displs = generator.controller.read_ints(
                    displs, self.process_count)

    def can_be_completed(self, gstate, state):
        return state.rank != self.root or self.remaining_processes_enter == 0

    def complete_main(self, generator, gstate, state):
        if state.rank == self.root:
            recvbuf = self.recvbuf
            controller = generator.controller
            size = types.get_datatype_size(self.sendtype)
            for vg_buffer, displ in zip(self.buffers, self.displs):
                controller.write_buffer(recvbuf + displ * size, vg_buffer.id)
        # Do nothing on non-root processes

    def compute_hash_data(self, hashthread):
        OperationWithBuffers.compute_hash_data(self, hashthread)
        hashthread.update(str(self.sendcounts))
        hashthread.update(str(self.sendtype))
        hashthread.update(str(self.recvbuf))
        hashthread.update(str(self.displs))


class Gather(OperationWithBuffers):

    name = "gather"

    def __init__(self, gstate, blocking, cc_id):
        OperationWithBuffers.__init__(self, gstate, blocking, cc_id)
        self.sendtype = None
        self.recvbuf = None
        self.count = None
        self.recvcount = None

    def enter_main(self,
                     generator,
                     gstate,
                     state,
                     args):
        sendbuf, sendcount, sendtype, \
               recvbuf, recvcount, recvtype, root, comm = args
        generator.validate_rank(root, 8)
        generator.validate_count(sendcount, 2)
        self.check_root(root)

        if self.root == root:
            self.recvbuf = recvbuf
            generator.validate_count(recvcount, 5)

        self.sendtype = sendtype
        self.sendcount = sendcount
        size = types.get_datatype_size(sendtype) * sendcount

        assert self.buffers[state.rank] is None
        self.buffers[state.rank] = generator.new_buffer(sendbuf, size)

    def can_be_completed(self, gstate, state):
        return state.rank != self.root or self.remaining_processes_enter == 0

    def complete_main(self, generator, gstate, state):
        if state.rank == self.root:
            recvbuf = self.recvbuf
            controller = generator.controller
            size = types.get_datatype_size(self.sendtype) * self.sendcount
            for i, vg_buffer in enumerate(self.buffers):
                controller.write_buffer(recvbuf + i * size, vg_buffer.id)
        # Do nothing on non-root processes

    def compute_hash_data(self, hashthread):
        OperationWithBuffers.compute_hash_data(self, hashthread)
        hashthread.update(str(self.sendcount))
        hashthread.update(str(self.sendtype))
        hashthread.update(str(self.recvbuf))


class Scatterv(OperationWithSingleBuffer):

    name = "scatterv"

    def __init__(self, gstate, blocking, cc_id):
        OperationWithSingleBuffer.__init__(self, gstate, blocking, cc_id)
        self.sendtype = None
        self.recvbufs = [ None ] * self.process_count
        self.recvcounts = [ None ] * self.process_count
        self.sendcounts = None
        self.displs = None

    def enter_main(self,
                     generator,
                     gstate,
                     state,
                     args):
        sendbuf, sendcounts, displs, sendtype, \
               recvbuf, recvcount, recvtype, root, comm = args
        generator.validate_rank(root, 8)
        generator.validate_count(recvcount, 5)
        self.check_root(root)
        self.recvbufs[state.rank] = recvbuf
        if self.root == state.rank:
            self.sendtype = sendtype
            self.sendcounts = generator.controller.read_ints(
                    sendcounts, self.process_count)
            self.displs = generator.controller.read_ints(
                    displs, self.process_count)
            sendcount = max(s + d for s, d in zip(self.sendcounts, self.displs))
            size = types.get_datatype_size(sendtype) * sendcount
            assert self.buffer is None
            self.buffer = generator.new_buffer(sendbuf, size)

    def can_be_completed(self, gstate, state):
        return self.buffer is not None

    def complete_main(self, generator, gstate, state):
        tsize = types.get_datatype_size(self.sendtype)
        size =  tsize * self.sendcounts[state.rank]
        index =  tsize * self.displs[state.rank]
        generator.controller.write_buffer(
                self.recvbufs[state.rank], self.buffer.id, index, size)

    def compute_hash_data(self, hashthread):
        OperationWithSingleBuffer.compute_hash_data(self, hashthread)
        hashthread.update(str(self.sendcounts))
        hashthread.update(str(self.sendtype))
        hashthread.update(str(self.recvbufs))
        hashthread.update(str(self.displs))


class Scatter(OperationWithSingleBuffer):

    name = "scatter"

    def __init__(self, gstate, blocking, cc_id):
        OperationWithSingleBuffer.__init__(self, gstate, blocking, cc_id)
        self.sendtype = None
        self.recvbufs = [ None ] * self.process_count
        self.sendcount = None
        self.displs = None

    def enter_main(self,
                     generator,
                     gstate,
                     state,
                     args):
        sendbuf, sendcount, sendtype, \
               recvbuf, recvcount, recvtype, root, comm = args
        generator.validate_count(sendcount, 2)
        generator.validate_count(recvcount, 5)
        generator.validate_rank(root, 8)
        self.check_root(root)
        self.recvbufs[state.rank] = recvbuf
        if self.root == state.rank:
            self.sendtype = sendtype
            self.sendcount = sendcount
            assert self.buffer is None
            size = (types.get_datatype_size(sendtype)
                        * self.sendcount * self.process_count)
            self.buffer = generator.new_buffer(sendbuf, size)

    def can_be_completed(self, gstate, state):
        return self.buffer is not None

    def complete_main(self, generator, gstate, state):
        size = types.get_datatype_size(self.sendtype) * self.sendcount
        index =  state.rank * size
        generator.controller.write_buffer(
                self.recvbufs[state.rank], self.buffer.id, index, size)

    def compute_hash_data(self, hashthread):
        OperationWithSingleBuffer.compute_hash_data(self, hashthread)
        hashthread.update(str(self.sendcount))
        hashthread.update(str(self.sendtype))
        hashthread.update(str(self.recvbufs))
