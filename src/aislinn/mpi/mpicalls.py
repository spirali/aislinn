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

from message import Message
import collectives
import event
import consts
import check
import errormsg
import types
import misc
import atypes as at
from comm import comm_id_name

# TODO: Universal architecture detection
POINTER_SIZE = 8
INT_SIZE = 4
STATUS_SIZE = 3 * INT_SIZE

def MPI_Finalize(generator, args, state, context):
    if state.finalized:
        e = errormsg.CallError()
        e.name = "doublefinalize"
        e.short_description = "MPI_Finalize was called twice"
        e.description = "MPI_Finalized was called twice"
        e.throw()

    state.finalized = True
    e = event.Event("MPI_Finalize", state.pid)
    generator.add_call_event(context, e)
    return False

def MPI_Finalized(generator, args, state, context):
    if state.finalized:
        flag = 1
    else:
        flag = 0
    generator.controller.write_int(args[0], flag)
    return False

def MPI_Comm_rank(generator, args, state, context):
    comm, ptr = args
    rank = comm.group.pid_to_rank(state.pid)
    if rank is None:
        rank = consts.MPI_UNDEFINED
    generator.controller.write_int(ptr, rank)
    return False

def MPI_Comm_size(generator, args, state, context):
    comm, ptr = args
    generator.controller.write_int(ptr, comm.group.size)
    return False

def MPI_Comm_group(generator, args, state, context):
    comm, group_ptr = args
    group_id = state.add_group(comm.group)
    generator.controller.write_int(group_ptr, group_id)
    return False

def MPI_Group_free(generator, args, state, context):
    group_ptr = args[0]
    group_id = generator.controller.read_int(group_ptr)
    group = check.check_and_get_group(state, group_id, 1)
    state.remove_group(group)
    generator.controller.write_int(group_ptr, consts.MPI_GROUP_NULL)
    return False

def MPI_Group_size(generator, args, state, context):
    group, ptr = args
    generator.controller.write_int(ptr, group.size)
    return False

def MPI_Type_size(generator, args, state, context):
    datatype, ptr = args
    generator.controller.write_int(ptr, datatype.size)
    return False

def MPI_Send(generator, args, state, context):
    return call_send(generator, args, state, context, True, "Send")

def MPI_Recv(generator, args, state, context):
    return call_recv(generator, args, state, context, True, "Recv")

def MPI_Isend(generator, args, state, context):
    return call_send(generator, args, state, context, False, "Isend")

def MPI_Irecv(generator, args, state, context):
    return call_recv(generator, args, state, context, False, "Irecv")

def MPI_Iprobe(generator, args, state, context):
    source, tag, comm, flag_ptr, status_ptr = args
    check.check_rank(comm, source, 1, True, True)
    e = event.CommEvent("Iprobe", state.pid, source, tag)
    generator.add_call_event(context, e)

    if source != consts.MPI_PROC_NULL:
        state.set_probe(comm, source, tag, flag_ptr, status_ptr)
    else:
        generator.controller.write_int(flag_ptr, 1)
        if status_ptr:
            generator.write_status(status_ptr,
                                   consts.MPI_PROC_NULL,
                                   consts.MPI_ANY_TAG,
                                   0)

        # We cannot simply return False, because we need to create state
        # (with hash), to detect possible cyclic computation
        state.set_ready()
    return True

def MPI_Probe(generator, args, state, context):
    source, tag, comm, status_ptr = args
    check.check_rank(comm, source, 1, True, True)
    e = event.CommEvent("Probe", state.pid, source, tag)
    generator.add_call_event(context, e)

    if source != consts.MPI_PROC_NULL:
        state.set_probe(comm, source, tag, None, status_ptr)
        return True
    else:
        if status_ptr:
            generator.write_status(status_ptr,
                                   consts.MPI_PROC_NULL,
                                   consts.MPI_ANY_TAG,
                                   0)
        return False

def MPI_Wait(generator, args, state, context):
    request_ptr, status_ptr = args

    request_ids = [ generator.controller.read_int(request_ptr) ]
    if status_ptr != consts.MPI_STATUSES_IGNORE:
        status_ptrs = [ status_ptr ]
    else:
        status_ptrs = None
    check.check_request_ids(state, request_ids)
    state.set_wait(request_ids, status_ptrs)

    e = event.WaitEvent("Wait", state.pid, request_ids)
    generator.add_call_event(context, e)
    return True

def MPI_Test(generator, args, state, context):
    request_ptr, flag_ptr, status_ptr = args
    request_ids = [ generator.controller.read_int(request_ptr) ]
    check.check_request_ids(state, request_ids)
    state.set_test(request_ids, flag_ptr)

    e = event.WaitEvent("Test", state.pid, request_ids)
    generator.add_call_event(context, e)
    return True

def MPI_Waitall(generator, args, state, context):
    count, requests_ptr, statuses_ptr = args
    request_ids = generator.controller.read_ints(requests_ptr, count)
    if statuses_ptr != consts.MPI_STATUSES_IGNORE:
        status_ptrs = [ statuses_ptr + i * STATUS_SIZE for i in xrange(count) ]
    else:
        status_ptrs = None

    check.check_request_ids(state, request_ids)
    state.set_wait(request_ids, status_ptrs)

    e = event.WaitEvent("Waitall", state.pid, request_ids)
    generator.add_call_event(context, e)
    return True

def MPI_Barrier(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Barrier,
                                     True,
                                     args)

def MPI_Gather(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Gather,
                                     True,
                                     args)

def MPI_Gatherv(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Gatherv,
                                     True,
                                     args)

def MPI_Scatter(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Scatter,
                                     True,
                                     args)

def MPI_Scatterv(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Scatterv,
                                     True,
                                     args)

def MPI_Reduce(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Reduce,
                                     True,
                                     args)

def MPI_Allreduce(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.AllReduce,
                                     True,
                                     args)

def MPI_Bcast(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Bcast,
                                     True,
                                     args)

def MPI_Ibarrier(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Barrier,
                                     False,
                                     args)

def MPI_Igather(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Gather,
                                     False,
                                     args)

def MPI_Igatherv(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Gatherv,
                                     False,
                                     args)

def MPI_Iscatter(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Scatter,
                                     False,
                                     args)

def MPI_Iscatterv(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Scatterv,
                                     False,
                                     args)

def MPI_Ireduce(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Reduce,
                                     False,
                                     args)

def MPI_Iallreduce(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.AllReduce,
                                     False,
                                     args)

def MPI_Ibcast(generator, args, state, context):
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Bcast,
                                     False,
                                     args)



def MPI_Comm_split(generator, args, state, context):
    comm = args[0]
    args = args[1:]
    op = state.gstate.call_collective_operation(
                generator, state, comm, collectives.CommSplit, True, args)
    request_id = state.add_collective_request(comm.comm_id, op.cc_id)
    state.set_wait((request_id,))
    return True

def MPI_Comm_dup(generator, args, state, context):
    comm, new_comm_ptr = args
    op = state.gstate.call_collective_operation(
                generator, state, comm, collectives.CommDup, True, new_comm_ptr)
    request_id = state.add_collective_request(comm.comm_id, op.cc_id)
    state.set_wait((request_id,))
    return True

def MPI_Comm_free(generator, args, state, context):
    comm_ptr = args[0]

    comm_id = generator.controller.read_int(comm_ptr)
    if comm_id == consts.MPI_COMM_WORLD or comm_id == consts.MPI_COMM_SELF:
        e = errormsg.CallError()
        e.name = "permanentcommfree"
        name = comm_id_name(comm_id)
        e.short_description = "{0} cannot be freed".format(name)
        e.description = "Communicator {0} cannot be freed".format(name)
        e.throw()
    comm = check.check_comm(state, comm_id, 1)
    state.remove_comm(comm)
    generator.controller.write_int(comm_ptr, consts.MPI_COMM_NULL);
    return False

def MPI_Get_count(generator, args, state, context):
    status_ptr, datatype, count_ptr = args
    size = generator.controller.read_int(status_ptr + 2 * INT_SIZE)
    result = datatype.get_count(size)
    if result is None:
        result = consts.MPI_UNDEFINED
    generator.controller.write_int(count_ptr, result)
    return False

def MPI_Type_contiguous(generator, args, state, context):
    count, datatype, newtype_ptr = args
    newtype = types.ContiguousType(datatype, count)
    state.add_datatype(newtype)
    generator.controller.write_int(newtype_ptr, newtype.type_id)
    return False

def MPI_Type_vector(generator, args, state, context):
    count, blocksize, stride, datatype, newtype_ptr = args
    newtype = types.VectorType(datatype, count, blocksize, stride, False)
    state.add_datatype(newtype)
    generator.controller.write_int(newtype_ptr, newtype.type_id)
    return False

def MPI_Type_hvector(generator, args, state, context):
    count, blocksize, stride, datatype, newtype_ptr = args
    newtype = types.VectorType(datatype, count, blocksize, stride, True)
    state.add_datatype(newtype)
    generator.controller.write_int(newtype_ptr, newtype.type_id)
    return False

def MPI_Type_indexed(generator, args, state, context):
    count, sizes_ptr, displs_ptr, datatype, newtype_ptr = args
    sizes = generator.controller.read_ints(sizes_ptr, count)
    check.check_sizes(sizes, 2)
    displs = generator.controller.read_ints(displs_ptr, count)
    newtype = types.IndexedType(datatype, count, sizes, displs, False)
    state.add_datatype(newtype)
    generator.controller.write_int(newtype_ptr, newtype.type_id)
    return False

def MPI_Type_create_hindexed(generator, args, state, context):
    count, sizes_ptr, displs_ptr, datatype, newtype_ptr = args
    sizes = generator.controller.read_ints(sizes_ptr, count)
    check.check_sizes(sizes, 2)
    displs = generator.controller.read_pointers(displs_ptr, count)
    newtype = types.IndexedType(datatype, count, sizes, displs, True)
    state.add_datatype(newtype)
    generator.controller.write_int(newtype_ptr, newtype.type_id)
    return False

def MPI_Type_hindexed(generator, args, state, context):
    return MPI_Type_create_hindexed(generator, args, state, context)

def MPI_Type_struct(generator, args, state, context):
    count, sizes_ptr, displs_ptr, types_ptr, newtype_ptr = args
    sizes = generator.controller.read_ints(sizes_ptr, count)
    check.check_sizes(sizes, 2)
    displs = generator.controller.read_pointers(displs_ptr, count)
    type_ids = generator.controller.read_ints(types_ptr, count)
    datatypes = check.check_datatypes(state, type_ids, 4, True)

    newtype = types.StructType(datatypes, sizes, displs)
    state.add_datatype(newtype)
    generator.controller.write_int(newtype_ptr, newtype.type_id)
    return False


def MPI_Type_commit(generator, args, state, context):
    datatype_ptr = args[0]
    type_id = generator.controller.read_int(datatype_ptr)
    datatype = check.check_datatype(state, type_id, 1, True)
    state.commit_datatype(datatype)
    return False

def MPI_Type_free(generator, args, state, context):
    datatype_ptr = args[0]
    type_id = generator.controller.read_int(datatype_ptr)
    datatype = check.check_datatype(state, type_id, 1, True)

    if datatype.is_buildin():
        e = errormsg.CallError()
        e.name = "remove-buildin-type"
        e.short_description = "Freeing predefined type"
        e.description = "Predefined datatype '{0}' cannot be freed" \
                .format(datatype.name)
        e.throw()

    state.remove_datatype(datatype)
    generator.controller.write_int(datatype_ptr, consts.MPI_DATATYPE_NULL)
    return False

def MPI_Dims_create(generator, args, state, context):
    nnodes, ndims, dims_ptr = args

    if ndims < 1:
        errormsg.InvalidArgument(ndims,
                                 2,
                                 "Invalid number of dimensions").throw()

    dims = generator.controller.read_ints(dims_ptr, ndims)
    count = 0
    for d in dims:
        if d < 0 or (d > 0 and nnodes % d != 0):
            errormsg.InvalidArgument(d,
                                     3,
                                     "Invalid dimension value").throw()
        if d > 0:
            nnodes /= d
        else:
            count += 1
    if count > 0:
        factors = misc.factors(nnodes, count)
        count = 0
        for i in xrange(len(dims)):
            if dims[i] == 0:
                dims[i] = factors[count]
                count += 1

    generator.controller.write_ints(dims_ptr, dims)
    return False

def call_collective_operation(generator,
                              state,
                              context,
                              op_class,
                              blocking,
                              args):
    if blocking:
        comm = args[-1]
        args = args[:-1]
    else:
        request_ptr = args[-1]
        comm = args[-2]
        args = args[:-2]

    op = state.gstate.call_collective_operation(
                generator, state, comm, op_class, blocking, args)
    request_id = state.add_collective_request(comm.comm_id, op.cc_id)
    if blocking:
        state.set_wait((request_id,))
    else:
        generator.controller.write_int(request_ptr, request_id)
    generator.add_call_event(context, op.get_event(state))
    return blocking

def make_send_request(generator, state, message):
    if generator.send_protocol == "randezvous":
        return state.add_synchronous_send_request(message)
    elif generator.send_protocol == "eager":
        return state.add_completed_request()
    elif generator.send_protocol == "dynamic":
        eager_threshold, randezvous_threshold = \
                state.gstate.send_protocol_thresholds
        if message.size < eager_threshold:
            return state.add_completed_request()
        elif message.size >= randezvous_threshold:
            return state.add_synchronous_send_request(message)
        else:
            return state.add_standard_send_request(message)
    elif generator.send_protocol == "threshold":
        if message.size < generator.send_protocol_eager_threshold:
            return state.add_completed_request()
        elif message.size >= generator.send_protocol_randezvous_threshold:
            return state.add_synchronous_send_request(message)
        else:
            return state.add_standard_send_request(message)
    else:
        assert generator.send_protocol == "full"
        return state.add_standard_send_request(message)

def call_send(generator, args, state, context, blocking, name):
    if blocking:
        buf_ptr, count, datatype, target, tag, comm = args
    else:
        buf_ptr, count, datatype, target, tag, comm, request_ptr = args

    check.check_rank(comm, target, 4, False, True)

    if target != consts.MPI_PROC_NULL:
        sz = count * datatype.size
        vg_buffer = generator.new_buffer_and_pack(datatype, count, buf_ptr)
        target_pid = comm.group.rank_to_pid(target)
        message = Message(
                comm.comm_id, state.get_rank(comm), target, tag, vg_buffer, sz)
        state.gstate.get_state(target_pid).add_message(message)
        request_id = make_send_request(generator, state, message)

        generator.message_sizes.add(datatype.size * count)
    else:
        request_id = state.add_completed_request()

    if blocking:
        state.set_wait((request_id,))
    else:
        generator.controller.write_int(request_ptr, request_id)

    e = event.CommEvent(name, state.pid, target, tag)
    generator.add_call_event(context, e)

    # TODO: Optimization : If message use eager protocol then nonblock
    return blocking

def call_recv(generator, args, state, context, blocking, name):
    buf_ptr, count, datatype, source, tag, comm, ptr = args
    check.check_rank(comm, source, 4, True, True)

    if blocking:
        status_ptr = ptr
    else:
        request_ptr = ptr

    e = event.CommEvent(name, state.pid, source, tag)
    generator.add_call_event(context, e)

    if source != consts.MPI_PROC_NULL or not blocking:
        request_id = state.add_recv_request(
                comm.comm_id, source, tag, buf_ptr, datatype, count)
    else:
        if status_ptr:
            generator.write_status(status_ptr,
                                   consts.MPI_PROC_NULL,
                                   consts.MPI_ANY_TAG,
                                   0)
        return False

    if blocking:
        if status_ptr:
            status_ptrs = [ status_ptr ]
        else:
            status_ptrs = None
        state.set_wait((request_id,), status_ptrs)
    else:
         generator.controller.write_int(request_ptr, request_id)

    # TODO: Optimization : If message is already here,
    # then non block and continue
    return blocking


class Call:

    def __init__(self, fn, args):
        self.fn = fn
        self.args = args

    @property
    def name(self):
        return self.fn.__name__

    def run(self, generator, args, state, context):
        assert len(args) == len(self.args)
        args = [ self.args[i].make_conversion(args[i], i, state)
                 for i in xrange(len(args)) ]
        return self.fn(generator, args, state, context)


calls = dict((c.name, c) for c in [
     Call(MPI_Finalize, ()),
     Call(MPI_Finalized, (at.Pointer,)),
     Call(MPI_Comm_rank, (at.Comm, at.Pointer)),
     Call(MPI_Comm_size, (at.Comm, at.Pointer)),
     Call(MPI_Comm_dup, (at.Comm, at.Pointer)),
     Call(MPI_Comm_split, (at.Comm, at.Int, at.Int, at.Pointer)),
     Call(MPI_Comm_free, (at.Pointer,)),
     Call(MPI_Comm_group, (at.Comm, at.Pointer)),
     Call(MPI_Group_free, (at.Pointer,)),
     Call(MPI_Group_size, (at.Group, at.Pointer)),
     Call(MPI_Send, (at.Pointer, at.Count, at.Datatype,
                     at.Rank, at.Tag, at.Comm)),
     Call(MPI_Isend, (at.Pointer, at.Count, at.Datatype,
                      at.Rank, at.Tag, at.Comm, at.Pointer)),
     Call(MPI_Recv, (at.Pointer, at.Count, at.Datatype,
                     at.Rank, at.TagAT, at.Comm, at.Pointer)),
     Call(MPI_Irecv, (at.Pointer, at.Count, at.Datatype,
                      at.Rank, at.TagAT, at.Comm, at.Pointer)),
     Call(MPI_Iprobe, (at.Int, at.TagAT, at.Comm, at.Pointer, at.Pointer)),
     Call(MPI_Probe, (at.Int, at.TagAT, at.Comm, at.Pointer)),
     Call(MPI_Wait, (at.Pointer, at.Pointer)),
     Call(MPI_Waitall, (at.Count, at.Pointer, at.Pointer)),
     Call(MPI_Test, (at.Pointer, at.Pointer, at.Pointer)),
     Call(MPI_Barrier, (at.Comm,)),
     Call(MPI_Gather, (at.Pointer, at.Count, at.Datatype,
                       at.Pointer, at.Int, at.Int,
                       at.Rank, at.Comm)),
     Call(MPI_Gatherv, (at.Pointer, at.Count, at.Datatype,
                         at.Pointer, at.Pointer, at.Pointer,
                         at.Int, at.Rank, at.Comm)),
     Call(MPI_Scatter, (at.Pointer, at.Int, at.Int,
                         at.Pointer, at.Count, at.Datatype,
                         at.Rank, at.Comm)),
     Call(MPI_Ibarrier, (at.Comm, at.Pointer)),
     Call(MPI_Ibcast, (at.Pointer, at.Count, at.Datatype,
                       at.Int, at.Comm, at.Pointer)),
     Call(MPI_Bcast, (at.Pointer, at.Count, at.Datatype,
                       at.Int, at.Comm)),
     Call(MPI_Reduce, (at.Pointer, at.Pointer, at.Count,
                       at.Datatype, at.Op, at.Int,
                       at.Comm)),
     Call(MPI_Allreduce, (at.Pointer, at.Pointer, at.Count,
                          at.Datatype, at.Op, at.Comm)),
     Call(MPI_Igather, (at.Pointer, at.Count, at.Datatype,
                        at.Pointer, at.Int, at.Int,
                        at.Rank, at.Comm, at.Pointer)),
     Call(MPI_Iscatter, (at.Pointer, at.Int, at.Int,
                         at.Pointer, at.Count, at.Datatype,
                         at.Rank, at.Comm, at.Pointer)),
     Call(MPI_Iscatterv, (at.Pointer, at.Pointer, at.Pointer, at.Int,
                          at.Pointer, at.Count, at.Datatype,
                          at.Rank, at.Comm, at.Pointer)),
     Call(MPI_Igatherv, (at.Pointer, at.Count, at.Datatype,
                         at.Pointer, at.Pointer, at.Pointer,
                         at.Int, at.Rank, at.Comm, at.Pointer)),
     Call(MPI_Ireduce, (at.Pointer, at.Pointer, at.Count,
                        at.Datatype, at.Op, at.Int,
                        at.Comm, at.Pointer)),
     Call(MPI_Iallreduce, (at.Pointer, at.Pointer, at.Count,
                           at.Datatype, at.Op, at.Comm, at.Pointer)),
     Call(MPI_Type_commit, (at.Pointer,)),
     Call(MPI_Type_size, (at.DatatypeU, at.Pointer)),
     Call(MPI_Type_free, (at.Pointer,)),
     Call(MPI_Type_contiguous, (at.Count, at.Datatype, at.Pointer)),
     Call(MPI_Type_vector, (at.Count, at.Count, at.Int,
                            at.DatatypeU, at.Pointer)),
     Call(MPI_Type_hvector, (at.Count, at.Count, at.Int,
                            at.DatatypeU, at.Pointer)),
     Call(MPI_Type_indexed, (at.Count, at.Pointer, at.Pointer,
                            at.DatatypeU, at.Pointer)),
     Call(MPI_Type_hindexed, (at.Count, at.Pointer, at.Pointer,
                            at.DatatypeU, at.Pointer)),
     Call(MPI_Type_create_hindexed, (at.Count, at.Pointer, at.Pointer,
                            at.DatatypeU, at.Pointer)),
     Call(MPI_Type_struct, (at.Count, at.Pointer, at.Pointer,
                            at.Pointer, at.Pointer)),
     Call(MPI_Get_count, (at.Pointer, at.Datatype, at.Pointer)),
     Call(MPI_Dims_create, (at.Int, at.Int, at.Pointer)),
     ])
