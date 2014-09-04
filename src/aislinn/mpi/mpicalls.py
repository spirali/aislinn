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
from base.utils import convert_types, convert_type
import collectives
import event
import consts
import check
import errormsg
from comm import comm_id_name

# TODO: Universal architecture detection
POINTER_SIZE = 8
INT_SIZE = 4
STATUS_SIZE = 3 * INT_SIZE

def MPI_Comm_rank(generator, args, state, context):
    comm_id, ptr = convert_types(args, ("int", "ptr"))
    comm = check.check_and_get_comm(state, comm_id, 1)
    rank = comm.group.pid_to_rank(state.pid)
    if rank is None:
        rank = consts.MPI_UNDEFINED
    generator.controller.write_int(ptr, rank)
    return False

def MPI_Comm_size(generator, args, state, context):
    comm_id, ptr = convert_types(args, ("int", "ptr"))
    comm = check.check_and_get_comm(state, comm_id, 1)
    generator.controller.write_int(ptr, comm.group.size)
    return False

def MPI_Type_size(generator, args, state, context):
    datatype_id, ptr = convert_types(args, ("int", "ptr"))
    datatype = check.check_datatype(state, datatype_id, 1)
    generator.controller.write_int(ptr, datatype.size)
    return False

def MPI_Send(generator, args, state, context):
    return call_send(generator, args, state, context, True, "Send")

def MPI_Recv(generator, args, state, context):
    return call_recv(generator, args, state, context, True, "Recv")

def MPI_ISend(generator, args, state, context):
    return call_send(generator, args, state, context, False, "Isend")

def MPI_IRecv(generator, args, state, context):
    return call_recv(generator, args, state, context, False, "Irecv")

def MPI_Wait(generator, args, state, context):
    request_ptr, status_ptr = \
        convert_types(args, ("ptr", # request_ptr
                             "ptr", # status_ptr
                             ))

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
    request_ptr, flag_ptr, status_ptr = \
        convert_types(args, ("ptr", # request_ptr
                             "ptr", # flag_ptr
                             "ptr", # status_ptr
                             ))


    request_ids = [ generator.controller.read_int(request_ptr) ]
    check.check_request_ids(state, request_ids)
    state.set_test(request_ids, flag_ptr)

    e = event.WaitEvent("Test", state.pid, request_ids)
    generator.add_call_event(context, e)
    return True

def MPI_Waitall(generator, args, state, context):
    count, requests_ptr, statuses_ptr = \
        convert_types(args, ("int", # count
                             "ptr", # request_ptr
                             "ptr", # status_ptr
                             ))

    count = int(count)
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
    args = convert_types(args, ("int",))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Barrier,
                                     True,
                                     args)

def MPI_Gather(generator, args, state, context):
    args = \
        convert_types(args,
                      ("ptr", # sendbuf
                       "int", # sendcount
                       "int", # sendtype
                       "ptr", # recvbuf
                       "int", # recvcount
                       "int", # recvtype
                       "int", # root
                       "int", # comm
                      ))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Gather,
                                     True,
                                     args)

def MPI_Gatherv(generator, args, state, context):
    args = \
        convert_types(args,
                      ("ptr", # sendbuf
                       "int", # sendcount
                       "int", # sendtype
                       "ptr", # recvbuf
                       "ptr", # recvcounts
                       "ptr", # displs
                       "int", # recvtype
                       "int", # root
                       "int", # comm
                      ))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Gatherv,
                                     True,
                                     args)

def MPI_Scatter(generator, args, state, context):
    args = \
        convert_types(args,
                      ("ptr", # sendbuf
                       "int", # sendcount
                       "int", # sendtype
                       "ptr", # recvbuf
                       "int", # recvcount
                       "int", # recvtype
                       "int", # root
                       "int", # comm
                      ))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Scatter,
                                     True,
                                     args)

def MPI_Scatterv(generator, args, state, context):
    args = \
        convert_types(args,
                      ("ptr", # sendbuf
                       "ptr", # sendcounts
                       "ptr", # displs
                       "int", # sendtype
                       "ptr", # recvbuf
                       "int", # recvcount
                       "int", # recvtype
                       "int", # root
                       "int", # comm
                      ))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Scatterv,
                                     True,
                                     args)

def MPI_Reduce(generator, args, state, context):
    args = \
        convert_types(args,
                      ("ptr", # sendbuf
                       "ptr", # recvbuf
                       "int", # count
                       "int", # datatype
                       "int", # op
                       "int", # root
                       "int", # comm
                      ))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Reduce,
                                     True,
                                     args)

def MPI_Allreduce(generator, args, state, context):
    args = \
        convert_types(args,
                      ("ptr", # sendbuf
                       "ptr", # recvbuf
                       "int", # count
                       "int", # datatype
                       "int", # op
                       "int", # comm
                      ))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.AllReduce,
                                     True,
                                     args)

def MPI_Bcast(generator, args, state, context):
    args = convert_types(args,
                         ("ptr", # buffer
                          "int", # count
                          "int", # datatype
                          "int", # root
                          "int", # comm
                         ))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Bcast,
                                     True,
                                     args)

def MPI_Ibarrier(generator, args, state, context):
    args = convert_types(args, ("int", "ptr"))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Barrier,
                                     False,
                                     args)

def MPI_Igather(generator, args, state, context):
    args = \
        convert_types(args,
                      ("ptr", # sendbuf
                       "int", # sendcount
                       "int", # sendtype
                       "ptr", # recvbuf
                       "int", # recvcount
                       "int", # recvtype
                       "int", # root
                       "int", # comm
                       "ptr", # request_ptr
                      ))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Gather,
                                     False,
                                     args)

def MPI_Igatherv(generator, args, state, context):
    args = \
        convert_types(args,
                      ("ptr", # sendbuf
                       "int", # sendcount
                       "int", # sendtype
                       "ptr", # recvbuf
                       "ptr", # recvcounts
                       "ptr", # displs
                       "int", # recvtype
                       "int", # root
                       "int", # comm
                       "ptr", # request_ptr
                      ))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Gatherv,
                                     False,
                                     args)

def MPI_Iscatter(generator, args, state, context):
    args = \
        convert_types(args,
                      ("ptr", # sendbuf
                       "int", # sendcount
                       "int", # sendtype
                       "ptr", # recvbuf
                       "int", # recvcount
                       "int", # recvtype
                       "int", # root
                       "int", # comm
                       "ptr", # request_ptr
                      ))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Scatter,
                                     False,
                                     args)

def MPI_Iscatterv(generator, args, state, context):
    args = \
        convert_types(args,
                      ("ptr", # sendbuf
                       "ptr", # sendcounts
                       "ptr", # displs
                       "int", # sendtype
                       "ptr", # recvbuf
                       "int", # recvcount
                       "int", # recvtype
                       "int", # root
                       "int", # comm
                       "ptr", # request_ptr
                      ))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Scatterv,
                                     False,
                                     args)

def MPI_Ireduce(generator, args, state, context):
    args = \
        convert_types(args,
                      ("ptr", # sendbuf
                       "ptr", # recvbuf
                       "int", # count
                       "int", # datatype
                       "int", # op
                       "int", # root
                       "int", # comm
                       "ptr", # request
                      ))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Reduce,
                                     False,
                                     args)

def MPI_Iallreduce(generator, args, state, context):
    args = \
        convert_types(args,
                      ("ptr", # sendbuf
                       "ptr", # recvbuf
                       "int", # count
                       "int", # datatype
                       "int", # op
                       "int", # comm
                       "ptr", # request
                      ))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.AllReduce,
                                     False,
                                     args)

def MPI_Ibcast(generator, args, state, context):
    args = convert_types(args,
                         ("ptr", # buffer
                          "int", # count
                          "int", # datatype
                          "int", # root
                          "int", # comm
                          "ptr", # request
                         ))
    return call_collective_operation(generator,
                                     state,
                                     context,
                                     collectives.Bcast,
                                     False,
                                     args)



def MPI_Comm_split(generator, args, state, context):
    args = convert_types(args,
                         ("int", # comm
                          "int", # color
                          "int", # key
                          "ptr", # newcomm
                         ))
    comm_id = args[0]
    args = args[1:]
    comm = check.check_and_get_comm(state, comm_id, 1)
    op = state.gstate.call_collective_operation(
                generator, state, comm, collectives.CommSplit, True, args)
    request_id = state.add_collective_request(comm_id, op.cc_id)
    state.set_wait((request_id,))
    return True

def MPI_Comm_dup(generator, args, state, context):
    comm_id, new_comm_ptr = convert_types(args,
                         ("int", # comm
                          "ptr", # newcomm
                         ))
    comm = check.check_and_get_comm(state, comm_id, 1)
    op = state.gstate.call_collective_operation(
                generator, state, comm, collectives.CommDup, True, new_comm_ptr)
    request_id = state.add_collective_request(comm_id, op.cc_id)
    state.set_wait((request_id,))
    return True



def MPI_Comm_free(generator, args, state, context):
    assert len(args) == 1
    comm_ptr = convert_type(args[0], "ptr")

    comm_id = generator.controller.read_int(comm_ptr)
    if comm_id == consts.MPI_COMM_WORLD or comm_id == consts.MPI_COMM_SELF:
        e = errormsg.CallError()
        e.name = "permanentcommfree"
        name = comm_id_name(comm_id)
        e.short_description = "{0} cannot be freed".format(name)
        e.description = "Communicator {0} cannot be freed".format(name)
        e.throw()
    comm = check.check_and_get_comm(state, comm_id, 1)
    state.remove_comm(comm)
    generator.controller.write_int(comm_ptr, consts.MPI_COMM_NULL);
    return False


def MPI_Get_count(generator, args, state, context):
    status_ptr, datatype_id, count_ptr = convert_types(args,
                                                       ("ptr", "int", "ptr"))
    datatype = check.check_datatype(state, datatype_id, 2)
    size = generator.controller.read_int(status_ptr + 2 * INT_SIZE)
    generator.controller.write_int(count_ptr, size / datatype.size)
    return False

def call_collective_operation(generator,
                              state,
                              context,
                              op_class,
                              blocking,
                              args):
    if blocking:
        comm_id = args[-1]
        args = args[:-1]
    else:
        request_ptr = args[-1]
        comm_id = args[-2]
        args = args[:-2]

    comm = check.check_and_get_comm(state, comm_id, len(args) + 1)
    op = state.gstate.call_collective_operation(
                generator, state, comm, op_class, blocking, args)
    request_id = state.add_collective_request(comm_id, op.cc_id)
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
        buf_ptr, count, datatype_id, target, tag, comm_id = \
            convert_types(args,
                          ("ptr", # buf_ptr
                           "int", # count
                           "int", # datatype
                           "int", # target
                           "int", # tag
                           "int", # comm
                          ))
    else:
        buf_ptr, count, datatype_id, target, tag, comm_id, request_ptr = \
            convert_types(args,
                          ("ptr", # buf_ptr
                           "int", # count
                           "int", # datatype
                           "int", # target
                           "int", # tag
                           "int", # comm
                           "ptr", # request_ptr
                          ))

    comm = check.check_and_get_comm(state, comm_id, 6)
    check.check_count(count, 2)
    check.check_rank(comm, target, 4, False)
    check.check_tag(tag, 5, False)
    datatype = check.check_datatype(state, datatype_id, 3)
    sz = count * datatype.size
    vg_buffer = generator.new_buffer_and_pack(datatype, count, buf_ptr)
    target_pid = comm.group.rank_to_pid(target)
    message = Message(comm_id, state.get_rank(comm), target, tag, vg_buffer, sz)
    state.gstate.get_state(target_pid).add_message(message)

    request_id = make_send_request(generator, state, message)
    if blocking:
        state.set_wait((request_id,))
    else:
        generator.controller.write_int(request_ptr, request_id)

    e = event.CommEvent(name, state.pid, target, tag)
    generator.add_call_event(context, e)

    # TODO: Optimization : If message use eager protocol then nonblock
    return blocking

def call_recv(generator, args, state, context, blocking, name):
    buf_ptr, count, datatype_id, source, tag, comm_id, ptr = \
        convert_types(args,
                      ("ptr", # buf_ptr
                       "int", # count
                       "int", # datatype
                       "int", # source
                       "int", # tag
                       "int", # comm
                       "ptr", # status_ptr (blocking) | request_ptr (nonblock)
                      ))
    if blocking:
        status_ptr = ptr
    else:
        request_ptr = ptr

    comm = check.check_and_get_comm(state, comm_id, 6)
    check.check_count(count, 2)
    check.check_rank(comm, source, 4, True)
    check.check_tag(tag, 5, True)

    datatype = check.check_datatype(state, datatype_id, 3)

    e = event.CommEvent(name, state.pid, source, tag)
    generator.add_call_event(context, e)

    request_id = state.add_recv_request(
            comm_id, source, tag, buf_ptr, datatype, count)

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

calls = {
        "MPI_Comm_rank" : MPI_Comm_rank,
        "MPI_Comm_size" : MPI_Comm_size,
        "MPI_Comm_split" : MPI_Comm_split,
        "MPI_Comm_dup" : MPI_Comm_dup,
        "MPI_Comm_free" : MPI_Comm_free,
        "MPI_Get_count" : MPI_Get_count,
        "MPI_Send" : MPI_Send,
        "MPI_Recv" : MPI_Recv,
        "MPI_Isend" : MPI_ISend,
        "MPI_Irecv" : MPI_IRecv,
        "MPI_Wait" : MPI_Wait,
        "MPI_Test" : MPI_Test,
        "MPI_Waitall" : MPI_Waitall,
        "MPI_Barrier" : MPI_Barrier,
        "MPI_Gather" : MPI_Gather,
        "MPI_Gatherv" : MPI_Gatherv,
        "MPI_Scatter" : MPI_Scatter,
        "MPI_Scatterv" : MPI_Scatterv,
        "MPI_Reduce" : MPI_Reduce,
        "MPI_Bcast" : MPI_Bcast,
        "MPI_Allreduce" : MPI_Allreduce,
        "MPI_Ibarrier" : MPI_Ibarrier,
        "MPI_Igather" : MPI_Igather,
        "MPI_Igatherv" : MPI_Igatherv,
        "MPI_Iscatter" : MPI_Iscatter,
        "MPI_Iscatterv" : MPI_Iscatterv,
        "MPI_Ireduce" : MPI_Ireduce,
        "MPI_Iallreduce" : MPI_Iallreduce,
        "MPI_Ibcast" : MPI_Ibcast,
        "MPI_Type_size" : MPI_Type_size,
}
