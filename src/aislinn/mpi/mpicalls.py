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

import collectives
import event
import consts
import check
import errormsg
import types
import ops
import misc
import atypes as at
from request import SendRequest, ReceiveRequest
from comm import comm_compare, group_compare, Group
from keyval import Keyval

import copy
import logging


def MPI_Initialized(context, args):
    # This is called only when MPI is already initialized, uninitialized MPI is
    # hanled in generator
    context.controller.write_int(args[0], 1)
    return False

def MPI_Finalize(context, args):
    if context.state.finalized:
        e = errormsg.DoubleFinalize(context)
        context.add_error_and_throw(e)
    context.state.finalized = True
    return False

def MPI_Finalized(context, args):
    if context.state.finalized:
        flag = 1
    else:
        flag = 0
    context.controller.write_int(args[0], flag)
    return False

def MPI_Abort(context, args):
    comm, exitcode = args
    context.add_error_and_throw(
        errormsg.AbortCalled(context, exitcode=exitcode))

def MPI_Comm_rank(context, args):
    comm, ptr = args
    rank = comm.group.pid_to_rank(context.state.pid)
    if rank is None:
        rank = consts.MPI_UNDEFINED
    context.controller.write_int(ptr, rank)
    return False

def MPI_Comm_size(context, args):
    comm, ptr = args
    context.controller.write_int(ptr, comm.group.size)
    return False

def MPI_Comm_group(context, args):
    comm, group_ptr = args
    group_id = context.state.add_group(comm.group)
    context.controller.write_int(group_ptr, group_id)
    return False

def MPI_Group_free(context, args):
    group_ptr = args[0]
    group_id = context.controller.read_int(group_ptr)
    group = check.check_and_get_group(context, group_id, 1)
    context.state.remove_group(group)
    context.controller.write_int(group_ptr, consts.MPI_GROUP_NULL)
    return False

def MPI_Group_size(context, args):
    group, ptr = args
    context.controller.write_int(ptr, group.size)
    return False

def MPI_Group_incl(context, args):
    # FIXME: If count == 0 then return MPI_GROUP_NULL
    group, count, ranks_ptr, group_ptr = args
    ranks = context.controller.read_ints(ranks_ptr, count)
    for rank in ranks:
        check.check_rank_in_group(context, group, rank, 3)
    table = [ group.rank_to_pid(rank) for rank in ranks ]
    group_id = context.state.add_group(Group(table))
    context.controller.write_int(group_ptr, group_id)
    return False

def MPI_Group_excl(context, args):
    # FIXME: If count == 0 then return MPI_GROUP_NULL
    group, count, ranks_ptr, group_ptr = args
    ranks = context.controller.read_ints(ranks_ptr, count)
    for rank in ranks:
        check.check_rank_in_group(context, group, rank, 3)
    check.check_unique_values(context, ranks, 3)
    table = [ group.rank_to_pid(rank)
              for rank in group.ranks
              if rank not in ranks ]
    group_id = context.state.add_group(Group(table))
    context.controller.write_int(group_ptr, group_id)
    return False

def MPI_Group_compare(context, args):
    group1, group2, ptr = args
    context.controller.write_int(ptr, group_compare(group1, group2))
    return False

def MPI_Type_size(context, args):
    datatype, ptr = args
    context.controller.write_int(ptr, datatype.size)
    return False

def MPI_Send(context, args):
    return call_send(context, args, True, "Send", "Send")

def MPI_Ssend(context, args):
    return call_send(context, args, True, "Ssend", "Ssend")

def MPI_Rsend(context, args):
    # TODO: Handle Rsend properly, now it is handled like a Ssend
    return call_send(context, args, True, "Ssend", "Rsend")

def MPI_Bsend(context, args):
    return call_send(context, args, True, "Bsend", "Bsend")

def MPI_Recv(context, args):
    return call_recv(context, args, True, "Recv")

def MPI_Isend(context, args):
    return call_send(context, args, False, "Send", "Isend")

def MPI_Issend(context, args):
    return call_send(context, args, False, "Ssend", "Issend")

def MPI_Irsend(context, args):
    # TODO: Handle Rsend properly, now it is handled like a Ssend
    return call_send(context, args, False, "Ssend", "Irsend")

def MPI_Ibsend(context, args):
    return call_send(context, args, False, "Bsend", "Ibsend")

def MPI_Irecv(context, args):
    return call_recv(context, args, False, "Irecv")

def MPI_Sendrecv(context, args):
    send_args = args[:5]
    send_args.append(args[-2]) # Add communicator
    recv_args = args[5:]
    send_request = call_send(context, send_args,
                             True, "Send", "Send", return_request=True)
    recv_request = call_recv(context, recv_args,
                             True, "Recv", return_request=True)
    context.state.set_wait((send_request.id, recv_request.id),
                   None, # request pointer
                   args[-1], # status pointer
                   immediate=True)
    return True

def MPI_Recv_init(context, args):
    return call_recv(
            context, args, False, "MPI_Recv_init", True)

def MPI_Send_init(context, args):
    return call_send(
            context, args, False, "Send", "Send_init", True)

def MPI_Bsend_init(context, args):
    return call_send(
            context, args, False, "Bsend", "Bsend_init", True)

def MPI_Ssend_init(context, args):
    return call_send(
            context, args, False, "Ssend", "Ssend_init", True)

def MPI_Rsend_init(context, args):
    # TODO: Handle Rsend properly, now it is handled like a Ssend
    return call_send(
            context, args, False, "Ssend", "Rsend_init", True)

def MPI_Start(context, args):
    request_id = context.controller.read_int(args[0])
    request = check.check_persistent_request(context, request_id, True, 1)
    context.state.activate_request(context, copy.copy(request), False)
    return False

def MPI_Startall(context, args):
    count, requests_ptr = args
    request_ids = context.controller.read_ints(requests_ptr, count)
    requests = [ check.check_persistent_request(context, request_id, True, 2, i)
                 for i, request_id in enumerate(request_ids) ]
    for request in requests:
        context.state.activate_request(context, copy.copy(request), False)
    return False

def MPI_Request_free(context, args):
    request_ptr = args[0]
    request_id = context.controller.read_int(request_ptr)
    request = check.check_persistent_request(context, request_id, False, 1)
    context.state.remove_persistent_request(request)
    context.controller.write_int(request_ptr, consts.MPI_REQUEST_NULL);
    return False

def MPI_Iprobe(context, args):
    source, tag, comm, flag_ptr, status_ptr = args
    check.check_rank(context, comm, source, 1, True, True)

    if source != consts.MPI_PROC_NULL:
        context.state.set_probe(comm, source, tag, flag_ptr, status_ptr)
    else:
        context.controller.write_int(flag_ptr, 1)
        if status_ptr:
            context.controller.write_status(status_ptr,
                                              consts.MPI_PROC_NULL,
                                              consts.MPI_ANY_TAG,
                                              0)

        # We cannot simply return False, because we need to create context.state
        # (with hash), to detect possible cyclic computation
        context.state.set_ready()
    return True

def MPI_Probe(context, args):
    source, tag, comm, status_ptr = args
    check.check_rank(context, comm, source, 1, True, True)

    if source != consts.MPI_PROC_NULL:
        context.state.set_probe(comm, source, tag, None, status_ptr)
        return True
    else:
        if status_ptr:
            context.controller.write_status(status_ptr,
                                              consts.MPI_PROC_NULL,
                                              consts.MPI_ANY_TAG,
                                              0)
        return False

def MPI_Wait(context, args):
    request_ptr, status_ptr = args

    request_id = context.controller.read_int(request_ptr)
    check.check_request_id(context, request_id, 1)
    if context.state.get_persistent_request(request_id) is None:
        context.controller.write_int(request_ptr, consts.MPI_REQUEST_NULL)
    context.state.set_wait([ request_id ], None, status_ptr)
    return True

def MPI_Test(context, args):
    request_ptr, flag_ptr, status_ptr = args
    request_id = context.controller.read_int(request_ptr)
    check.check_request_id(context, request_id, 1)
    context.state.set_test([ request_id ], flag_ptr, request_ptr, status_ptr)
    return True

def MPI_Waitall(context, args):
    count, requests_ptr, status_ptr = args
    if count == 0:
        return False
    request_ids = context.controller.read_ints(requests_ptr, count)
    check.check_request_ids(context, request_ids, 2)
    values = []
    for request_id in request_ids:
        if context.state.get_persistent_request(request_id) is None:
            values.append(consts.MPI_REQUEST_NULL)
        else:
            values.append(request_id)
    context.controller.write_ints(requests_ptr, values)
    context.state.set_wait(request_ids, None, status_ptr)
    return True

def MPI_Waitany(context, args):
    count, requests_ptr, index_ptr, status_ptr = args
    request_ids = context.controller.read_ints(requests_ptr, count)

    for i, request_id in enumerate(request_ids):
        if request_id == consts.MPI_REQUEST_NULL:
            continue
        if context.state.get_persistent_request(request_id) is None:
            check.check_request_id(context, request_id, 2, i)
        elif not context.state.get_request(request_id):
            request_ids[i] = consts.MPI_REQUEST_NULL
    if all(id == consts.MPI_REQUEST_NULL for id in request_ids):
        context.controller.write_int(index_ptr, consts.MPI_UNDEFINED)
        return False
    context.state.set_wait(request_ids, requests_ptr, status_ptr,
                   status=context.state.StatusWaitAny, index_ptr=index_ptr)
    return True

def MPI_Waitsome(context, args):
    count, requests_ptr, outcount_ptr, indices_ptr, status_ptr = args
    request_ids = context.controller.read_ints(requests_ptr, count)

    for i, request_id in enumerate(request_ids):
        if request_id == consts.MPI_REQUEST_NULL:
            continue
        if context.state.get_persistent_request(request_id) is None:
            check.check_request_id(context, request_id, 2, i)
        elif not context.state.get_request(request_id):
            request_ids[i] = consts.MPI_REQUEST_NULL
    if all(id == consts.MPI_REQUEST_NULL for id in request_ids):
        context.controller.write_int(outcount_ptr, consts.MPI_UNDEFINED)
        return False
    context.state.set_wait(request_ids, requests_ptr, status_ptr,
                   status=context.state.StatusWaitSome,
                   index_ptr=(indices_ptr, outcount_ptr))
    return True

def MPI_Testall(context, args):
    count, requests_ptr, flag_ptr, status_ptr = args
    if count == 0:
        return False
    request_ids = context.controller.read_ints(requests_ptr, count)
    check.check_request_ids(context, request_ids, 2)
    context.state.set_test(request_ids, flag_ptr, requests_ptr, status_ptr)
    return True

def MPI_Barrier(context, args):
    return call_collective_operation(context,
                                     collectives.Barrier,
                                     True,
                                     args)

def MPI_Gather(context, args):
    return call_collective_operation(context,
                                     collectives.Gather,
                                     True,
                                     args)

def MPI_Allgather(context, args):
    return call_collective_operation(context,
                                     collectives.Allgather,
                                     True,
                                     args)

def MPI_Gatherv(context, args):
    return call_collective_operation(context,
                                     collectives.Gatherv,
                                     True,
                                     args)

def MPI_Allgatherv(context, args):
    return call_collective_operation(context,
                                     collectives.Allgatherv,
                                     True,
                                     args)

def MPI_Scatter(context, args):
    return call_collective_operation(context,
                                     collectives.Scatter,
                                     True,
                                     args)

def MPI_Scatterv(context, args):
    return call_collective_operation(context,
                                     collectives.Scatterv,
                                     True,
                                     args)

def MPI_Reduce(context, args):
    return call_collective_operation(context,
                                     collectives.Reduce,
                                     True,
                                     args)

def MPI_Reduce_scatter(context, args):
    return call_collective_operation(context,
                                     collectives.ReduceScatter,
                                     True,
                                     args)

def MPI_Allreduce(context, args):
    return call_collective_operation(context,
                                     collectives.AllReduce,
                                     True,
                                     args)

def MPI_Scan(context, args):
    return call_collective_operation(context,
                                     collectives.Scan,
                                     True,
                                     args)

def MPI_Bcast(context, args):
    return call_collective_operation(context,
                                     collectives.Bcast,
                                     True,
                                     args)

def MPI_Ibarrier(context, args):
    return call_collective_operation(context,
                                     collectives.Barrier,
                                     False,
                                     args)

def MPI_Igather(context, args):
    return call_collective_operation(context,
                                     collectives.Gather,
                                     False,
                                     args)

def MPI_Igatherv(context, args):
    return call_collective_operation(context,
                                     collectives.Gatherv,
                                     False,
                                     args)

def MPI_Iscatter(context, args):
    return call_collective_operation(context,
                                     collectives.Scatter,
                                     False,
                                     args)

def MPI_Iscatterv(context, args):
    return call_collective_operation(context,
                                     collectives.Scatterv,
                                     False,
                                     args)

def MPI_Ireduce(context, args):
    return call_collective_operation(context,
                                     collectives.Reduce,
                                     False,
                                     args)

def MPI_Iallreduce(context, args):
    return call_collective_operation(context,
                                     collectives.AllReduce,
                                     False,
                                     args)

def MPI_Ibcast(context, args):
    return call_collective_operation(context,
                                     collectives.Bcast,
                                     False,
                                     args)


def MPI_Op_create(context, args):
    fn_ptr, commute, op_ptr = args
    op = ops.UserDefinedOperation(bool(commute), fn_ptr)
    context.state.add_op(op)
    context.controller.write_int(op_ptr, op.op_id)
    return False

def MPI_Op_free(context, args):
    op_ptr = args[0]
    op_id = context.controller.read_int(op_ptr)
    op = check.check_op(context, op_id, 1)
    context.state.remove_op(op)
    context.controller.write_int(op_ptr, consts.MPI_OP_NULL)
    return False

def MPI_Comm_split(context, args):
    comm = args[0]
    args = args[1:]
    op = context.state.gstate.call_collective_operation(
                context, comm, collectives.CommSplit, True, args)
    request_id = context.state.add_collective_request(comm, op.cc_id)
    context.state.set_wait((request_id,))
    return True

def MPI_Comm_dup(context, args):
    comm, new_comm_ptr = args
    op = context.state.gstate.call_collective_operation(
                context, comm, collectives.CommDup, True, new_comm_ptr)
    request_id = context.state.add_collective_request(comm, op.cc_id)
    context.state.set_wait((request_id,))
    return True

def MPI_Comm_compare(context, args):
    comm1, comm2, result_ptr = args
    context.controller.write_int(result_ptr,
                                   comm_compare(comm1, comm2))
    return False

def MPI_Comm_free(context, args):
    comm_ptr = args[0]

    comm_id = context.controller.read_int(comm_ptr)
    if comm_id == consts.MPI_COMM_WORLD or comm_id == consts.MPI_COMM_SELF:
        e = errormsg.FreeingPermanentComm(context, comm_id=comm_id)
        context.add_error_and_throw(e)
    comm = check.check_comm(context, comm_id, 1)
    context.state.remove_comm(context, comm)
    context.controller.write_int(comm_ptr, consts.MPI_COMM_NULL);
    return False

def MPI_Get_count(context, args):
    status_ptr, datatype, count_ptr = args
    size = context.controller.read_int(
            status_ptr + 2 * context.controller.INT_SIZE)
    result = datatype.get_count(size)
    if result is None:
        result = consts.MPI_UNDEFINED
    context.controller.write_int(count_ptr, result)
    return False

def MPI_Get_processor_name(context, args):
    name_ptr, len_ptr = args

    if "Ok" != context.controller.is_writable(
            name_ptr, consts.MPI_MAX_PROCESSOR_NAME):
        context.add_error_and_throw(
                errormsg.InvalidBufferForProcessorName(context))

    name = "Processor-{0}".format(context.state.pid)
    assert len(name) < consts.MPI_MAX_PROCESSOR_NAME - 1

    # Memory do not have to be checked again
    context.controller.write_string(name_ptr, name, check=False)
    context.controller.write_int(len_ptr, len(name))
    return False


def MPI_Type_contiguous(context, args):
    count, datatype, newtype_ptr = args
    newtype = types.ContiguousType(datatype, count)
    context.state.add_datatype(newtype)
    context.controller.write_int(newtype_ptr, newtype.type_id)
    return False

def MPI_Type_vector(context, args):
    count, blocksize, stride, datatype, newtype_ptr = args
    newtype = types.VectorType(datatype, count, blocksize, stride, False)
    context.state.add_datatype(newtype)
    context.controller.write_int(newtype_ptr, newtype.type_id)
    return False

def MPI_Type_hvector(context, args):
    count, blocksize, stride, datatype, newtype_ptr = args
    newtype = types.VectorType(datatype, count, blocksize, stride, True)
    context.state.add_datatype(newtype)
    context.controller.write_int(newtype_ptr, newtype.type_id)
    return False

def MPI_Type_indexed(context, args):
    count, sizes_ptr, displs_ptr, datatype, newtype_ptr = args
    sizes = context.controller.read_ints(sizes_ptr, count)
    check.check_sizes(context, sizes, 2)
    displs = context.controller.read_ints(displs_ptr, count)
    newtype = types.IndexedType(datatype, count, sizes, displs, False)
    context.state.add_datatype(newtype)
    context.controller.write_int(newtype_ptr, newtype.type_id)
    return False

def MPI_Type_create_hindexed(context, args):
    count, sizes_ptr, displs_ptr, datatype, newtype_ptr = args
    sizes = context.controller.read_ints(sizes_ptr, count)
    check.check_sizes(context, sizes, 2)
    displs = context.controller.read_pointers(displs_ptr, count)
    newtype = types.IndexedType(datatype, count, sizes, displs, True)
    context.state.add_datatype(newtype)
    context.controller.write_int(newtype_ptr, newtype.type_id)
    return False

def MPI_Type_hindexed(context, args):
    return MPI_Type_create_hindexed(context, args)

def MPI_Type_create_struct(context, args):
    count, sizes_ptr, displs_ptr, types_ptr, newtype_ptr = args
    sizes = context.controller.read_ints(sizes_ptr, count)
    check.check_sizes(context, sizes, 2)
    displs = context.controller.read_pointers(displs_ptr, count)
    type_ids = context.controller.read_ints(types_ptr, count)
    datatypes = check.check_datatypes(context, type_ids, 4, True)

    newtype = types.StructType(datatypes, sizes, displs)
    context.state.add_datatype(newtype)
    context.controller.write_int(newtype_ptr, newtype.type_id)
    return False

def MPI_Type_struct(context, args):
    return MPI_Type_create_struct(context, args)

def MPI_Type_commit(context, args):
    datatype_ptr = args[0]
    type_id = context.controller.read_int(datatype_ptr)
    datatype = check.check_datatype(context, type_id, 1, True)
    context.state.commit_datatype(datatype)
    return False

def MPI_Type_free(context, args):
    datatype_ptr = args[0]
    type_id = context.controller.read_int(datatype_ptr)
    datatype = check.check_datatype(context, type_id, 1, True)

    if datatype.is_buildin():
        e = errormsg.RemovingBuildinDatatype(context, datatype=datatype)
        context.add_error_and_throw(e)

    context.state.remove_datatype(datatype)
    context.controller.write_int(datatype_ptr, consts.MPI_DATATYPE_NULL)
    return False

def MPI_Dims_create(context, args):
    nnodes, ndims, dims_ptr = args

    if ndims < 1:
        e = errormsg.InvalidArgument(ndims,
                                 2,
                                 "Invalid number of dimensions")
        context.add_error_and_throw(e)


    dims = context.controller.read_ints(dims_ptr, ndims)
    count = 0
    for d in dims:
        if d < 0 or (d > 0 and nnodes % d != 0):
            e = errormsg.InvalidArgument(d,
                                     3,
                                     "Invalid dimension value")
            context.add_error_and_throw(e)
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

    context.controller.write_ints(dims_ptr, dims)
    return False

def MPI_Comm_set_errhandler(context, args):
    # Currently we can do nothing, because error is never returned
    return False

def MPI_Comm_create_keyval(context, args):
    copy_fn, delete_fn, keyval_ptr, extra_ptr = args
    keyval = Keyval(copy_fn, delete_fn, extra_ptr)
    context.state.add_keyval(keyval)
    context.controller.write_int(keyval_ptr, keyval.keyval_id)
    return False

def MPI_Comm_free_keyval(context, args):
    keyval_ptr = args[0]
    keyval_id = context.controller.read_int(keyval_ptr)
    keyval = check.check_keyval(context, keyval_id, 1)
    context.state.remove_keyval(keyval)
    context.controller.write_int(keyval_ptr, consts.MPI_KEYVAL_INVALID)
    return False

def MPI_Comm_get_attr(context, args):
    comm, keyval, value_ptr, flag_ptr = args
    if keyval.keyval_id == consts.MPI_TAG_UB:
        value = context.generator.get_const_ptr(consts.MPI_TAG_UB)
    else:
        value = context.state.get_attr(comm, keyval)
    if value is not None:
        context.controller.write_pointer(value_ptr, value)
        context.controller.write_int(flag_ptr, 1)
    else:
        context.controller.write_int(flag_ptr, 0)
    return False

def MPI_Comm_set_attr(context, args):
    comm, keyval, value = args
    context.state.set_attr(context, comm, keyval, value)
    return False

def MPI_Comm_delete_attr(context, args):
    comm, keyval = args
    if context.state.get_attr(comm, keyval) is None:
        e = errormsg.AttributeNotFound(context)
        context.add_error_and_throw(e)
    context.state.delete_attr(context, comm, keyval)
    return False

def MPI_Keyval_create(context, args):
    return MPI_Comm_create_keyval(context, args)

def MPI_Keyval_free(context, args):
    return MPI_Comm_free_keyval(context, args)

def MPI_Attr_get(context, args):
    return MPI_Comm_get_attr(context, args)

def MPI_Attr_put(context, args):
    return MPI_Comm_set_attr(context, args)

def MPI_Attr_delete(context, args):
    return MPI_Comm_delete_attr(context, args)

def call_collective_operation(context,
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

    op = context.state.gstate.call_collective_operation(
                context, comm, op_class, blocking, args)
    request_id = context.state.add_collective_request(comm, op.cc_id)
    if blocking:
        context.state.set_wait((request_id,))
    else:
        context.controller.write_int(request_ptr, request_id)
    return blocking

def get_send_type(generator, state, mode, datatype, count):
    if mode == "Ssend" \
       or (mode == "Send" and generator.send_protocol == "rendezvous"):
        return SendRequest.Synchronous
    elif mode == "Bsend" \
       or (mode == "Send" and generator.send_protocol == "eager"):
        return SendRequest.Buffered
    elif generator.send_protocol == "dynamic":
        size = datatype.size * count
        eager_threshold, rendezvous_threshold = \
                state.gstate.send_protocol_thresholds
        if size < eager_threshold:
            return SendRequest.Buffered
        elif size >= rendezvous_threshold:
            return SendRequest.Synchronous
        else:
            return SendRequest.Standard
    elif generator.send_protocol == "threshold":
        size = datatype.size * count
        if size < generator.send_protocol_eager_threshold:
            return SendRequest.Buffered
        elif size >= generator.send_protocol_rendezvous_threshold:
            return SendRequest.Synchronous
        else:
            return SendRequest.Standard
    else:
        assert generator.send_protocol == "full"
        return SendRequest.Standard

def call_send(context, args,
              blocking, mode, name, persistent=False, return_request=False):
    context.state = context.state
    if blocking:
        data_ptr, count, datatype, target, tag, comm = args
    else:
        data_ptr, count, datatype, target, tag, comm, request_ptr = args

    check.check_rank(context, comm, target, 4, False, True)

    send_type = get_send_type(
            context.gcontext.generator, context.state, mode, datatype, count)
    request = SendRequest(context.state.new_request_id(), send_type,
                          comm, target, tag, data_ptr, datatype, count)
    if persistent:
        assert not blocking
        context.state.add_persistent_request(request)
    else:
        context.state.activate_request(context, request, blocking)

    if return_request:
        return request

    if blocking:
        context.state.set_wait((request.id,), immediate=True)
    else:
        context.controller.write_int(request_ptr, request.id)
    return blocking

def call_recv(context, args, blocking, name, persistent=False, return_request=False):
    data_ptr, count, datatype, source, tag, comm, ptr = args
    check.check_rank(context, comm, source, 4, True, True)

    if blocking:
        status_ptr = ptr
    else:
        request_ptr = ptr

    if blocking and source == consts.MPI_PROC_NULL:
        if status_ptr:
            context.controller.write_status(status_ptr,
                                            consts.MPI_PROC_NULL,
                                            consts.MPI_ANY_TAG,
                                            0)
        return False

    request = ReceiveRequest(
            context.state.new_request_id(), comm, source, tag, data_ptr, datatype, count)

    if persistent:
        assert not blocking
        context.state.add_persistent_request(request)
    else:
        context.state.activate_request(context, request, blocking)

    if return_request:
        return request

    if blocking:
        context.state.set_wait((request.id,), None, status_ptr, immediate=True)
    else:
        context.controller.write_int(request_ptr, request.id)
    return blocking


class Call:

    def __init__(self, fn, args):
        self.fn = fn
        self.args = args

    @property
    def name(self):
        return self.fn.__name__

    def run(self, context, args):
        assert len(args) == len(self.args)
        e = event.CallEvent(self.name,
                            context.state.pid,
                            ",".join(args))
        e.stacktrace = context.controller.get_stacktrace()
        context.event = e
        context.gcontext.add_event(e)
        r = self.fn(context,
                    [ self.args[i].make_conversion(args[i], i + 1, context)
                      for i in xrange(len(args)) ])
        context.event = None
        return r


calls_communicating = dict((c.name, c) for c in [
     Call(MPI_Comm_dup, (at.Comm, at.Pointer)),
     Call(MPI_Comm_split, (at.Comm, at.Int, at.Int, at.Pointer)),
     Call(MPI_Send, (at.Pointer, at.Count, at.Datatype,
                     at.Rank, at.Tag, at.Comm)),
     Call(MPI_Bsend, (at.Pointer, at.Count, at.Datatype,
                     at.Rank, at.Tag, at.Comm)),
     Call(MPI_Ssend, (at.Pointer, at.Count, at.Datatype,
                     at.Rank, at.Tag, at.Comm)),
     Call(MPI_Rsend, (at.Pointer, at.Count, at.Datatype,
                     at.Rank, at.Tag, at.Comm)),
     Call(MPI_Isend, (at.Pointer, at.Count, at.Datatype,
                      at.Rank, at.Tag, at.Comm, at.Pointer)),
     Call(MPI_Issend, (at.Pointer, at.Count, at.Datatype,
                      at.Rank, at.Tag, at.Comm, at.Pointer)),
     Call(MPI_Ibsend, (at.Pointer, at.Count, at.Datatype,
                      at.Rank, at.Tag, at.Comm, at.Pointer)),
     Call(MPI_Irsend, (at.Pointer, at.Count, at.Datatype,
                      at.Rank, at.Tag, at.Comm, at.Pointer)),
     Call(MPI_Recv, (at.Pointer, at.Count, at.Datatype,
                     at.Rank, at.TagAT, at.Comm, at.StatusPtr)),
     Call(MPI_Irecv, (at.Pointer, at.Count, at.Datatype,
                      at.Rank, at.TagAT, at.Comm, at.Pointer)),
     Call(MPI_Sendrecv, (at.Pointer, at.Count, at.Datatype, at.Rank, at.Tag,
                         at.Pointer, at.Count, at.Datatype, at.Rank, at.TagAT,
                         at.Comm, at.StatusPtr)),
     Call(MPI_Recv_init, (at.Pointer, at.Count, at.Datatype,
                          at.Rank, at.TagAT, at.Comm, at.Pointer)),
     Call(MPI_Send_init, (at.Pointer, at.Count, at.Datatype,
                      at.Rank, at.Tag, at.Comm, at.Pointer)),
     Call(MPI_Bsend_init, (at.Pointer, at.Count, at.Datatype,
                      at.Rank, at.Tag, at.Comm, at.Pointer)),
     Call(MPI_Ssend_init, (at.Pointer, at.Count, at.Datatype,
                      at.Rank, at.Tag, at.Comm, at.Pointer)),
     Call(MPI_Rsend_init, (at.Pointer, at.Count, at.Datatype,
                      at.Rank, at.Tag, at.Comm, at.Pointer)),
     Call(MPI_Start, (at.Pointer,)),
     Call(MPI_Startall, (at.Count, at.Pointer,)),
     Call(MPI_Iprobe, (at.Int, at.TagAT, at.Comm, at.Pointer, at.Pointer)),
     Call(MPI_Iprobe, (at.Int, at.TagAT, at.Comm, at.Pointer, at.Pointer)),
     Call(MPI_Probe, (at.Int, at.TagAT, at.Comm, at.Pointer)),
     Call(MPI_Wait, (at.Pointer, at.StatusPtr)),
     Call(MPI_Waitall, (at.Count, at.Pointer, at.StatusesPtr)),
     Call(MPI_Waitany, (at.Count, at.Pointer, at.Pointer, at.StatusPtr)),
     Call(MPI_Waitsome, (at.Count, at.Pointer, at.Pointer, at.Pointer, at.StatusesPtr)),
     Call(MPI_Test, (at.Pointer, at.Pointer, at.StatusPtr)),
     Call(MPI_Testall, (at.Count, at.Pointer, at.Pointer, at.StatusesPtr)),
     Call(MPI_Barrier, (at.Comm,)),
     Call(MPI_Gather, (at.Pointer, at.Count, at.Datatype,
                       at.Pointer, at.Int, at.Int,
                       at.Rank, at.Comm)),
     Call(MPI_Gatherv, (at.Pointer, at.Count, at.Datatype,
                        at.Pointer, at.Pointer, at.Pointer,
                        at.Int, at.Rank, at.Comm)),
     Call(MPI_Allgather, (at.Pointer, at.Count, at.Datatype,
                       at.Pointer, at.Int, at.Int, at.Comm)),
     Call(MPI_Allgatherv, (at.Pointer, at.Count, at.Datatype,
                           at.Pointer, at.Pointer, at.Pointer,
                           at.Int, at.Comm)),
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
     Call(MPI_Reduce_scatter, (at.Pointer, at.Pointer, at.Pointer,
                       at.Datatype, at.Op, at.Comm)),
     Call(MPI_Allreduce, (at.Pointer, at.Pointer, at.Count,
                          at.Datatype, at.Op, at.Comm)),
     Call(MPI_Scan, (at.Pointer, at.Pointer, at.Count,
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
])

calls_non_communicating = dict((c.name, c) for c in [
     Call(MPI_Initialized, (at.Pointer,)),
     Call(MPI_Finalize, ()),
     Call(MPI_Finalized, (at.Pointer,)),
     Call(MPI_Comm_rank, (at.Comm, at.Pointer)),
     Call(MPI_Comm_size, (at.Comm, at.Pointer)),
     Call(MPI_Comm_free, (at.Pointer,)),
     Call(MPI_Comm_compare, (at.Comm, at.Comm, at.Pointer)),
     Call(MPI_Comm_group, (at.Comm, at.Pointer)),
     Call(MPI_Group_free, (at.Pointer,)),
     Call(MPI_Group_size, (at.Group, at.Pointer)),
     Call(MPI_Group_incl, (at.Group, at.Count, at.Pointer, at.Pointer)),
     Call(MPI_Group_excl, (at.Group, at.Count, at.Pointer, at.Pointer)),
     Call(MPI_Group_compare, (at.Group, at.Group, at.Pointer)),
     Call(MPI_Request_free, (at.Pointer,)),
     Call(MPI_Op_create, (at.Pointer, at.Int, at.Pointer)),
     Call(MPI_Op_free, (at.Pointer,)),
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
     Call(MPI_Type_create_struct, (at.Count, at.Pointer, at.Pointer,
                                   at.Pointer, at.Pointer)),
     Call(MPI_Type_struct, (at.Count, at.Pointer, at.Pointer,
                            at.Pointer, at.Pointer)),
     Call(MPI_Get_count, (at.Pointer, at.Datatype, at.Pointer)),
     Call(MPI_Get_processor_name, (at.Pointer, at.Pointer)),
     Call(MPI_Dims_create, (at.Int, at.Int, at.Pointer)),
     Call(MPI_Dims_create, (at.Int, at.Int, at.Pointer)),
     Call(MPI_Comm_set_errhandler, (at.Comm, at.Pointer)),
     Call(MPI_Comm_create_keyval, (at.Pointer, at.Pointer, at.Pointer, at.Pointer)),
     Call(MPI_Comm_free_keyval, (at.Pointer,)),
     Call(MPI_Comm_get_attr, (at.Comm, at.Keyval, at.Pointer, at.Pointer)),
     Call(MPI_Comm_set_attr, (at.Comm, at.Keyval, at.Pointer)),
     Call(MPI_Comm_delete_attr, (at.Comm, at.Keyval)),
     Call(MPI_Keyval_create, (at.Pointer, at.Pointer, at.Pointer, at.Pointer)),
     Call(MPI_Keyval_free, (at.Pointer,)),
     Call(MPI_Attr_get, (at.Comm, at.Keyval, at.Pointer, at.Pointer)),
     Call(MPI_Attr_put, (at.Comm, at.Keyval, at.Pointer)),
     Call(MPI_Attr_delete, (at.Comm, at.Keyval)),
     Call(MPI_Abort, (at.Comm, at.Int)),
])
