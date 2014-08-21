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

from base.utils import convert_types
import collectives
import event

# TODO: Universal architecture detection
POINTER_SIZE = 8

def MPI_Comm_rank(generator, args, gstate, state, context):
    assert len(args) == 2
    generator.controller.write_int(args[1], state.rank)
    return False

def MPI_Comm_size(generator, args, gstate, state, context):
    assert len(args) == 2
    generator.controller.write_int(args[1], generator.process_count)
    return False

def MPI_Send(generator, args, gstate, state, context):
    buf_ptr, count, datatype, target, tag, comm = \
        convert_types(args,
                      ("ptr", # buf_ptr
                       "int", # count
                       "int", # datatype
                       "int", # target
                       "int", # tag
                       "int", # comm
                      ))
    generator.validate_count(count, 2)
    generator.validate_rank(target, 4, False)
    generator.validate_tag(tag, 5, False)
    size = count * generator.get_datatype_size(datatype, 3)
    buffer_id, hash = generator.controller.new_buffer(buf_ptr, size, hash=True)
    vg_buffer = generator.vg_buffers.new(buffer_id)
    message = gstate.get_state(target).add_message(
            state.rank, target, tag, vg_buffer, size, hash)

    e = event.CommEvent("Send", state.rank, target, tag)
    generator.add_call_event(context, e)

    request_ids = (generator.make_send_request(gstate, state, message),)
    state.set_wait(request_ids)
    # TODO: Optimization : If message use eager protocol then nonblock
    return True

def MPI_Recv(generator, args, gstate, state, context):
    buf_ptr, count, datatype, source, tag, comm, status_ptr = \
        convert_types(args,
                      ("ptr", # buf_ptr
                       "int", # count
                       "int", # datatype
                       "int", # source
                       "int", # tag
                       "int", # comm
                       "ptr", # status
                      ))

    generator.validate_count(count, 2)
    generator.validate_rank(source, 4, True)
    generator.validate_tag(tag, 5, True)

    size = count * generator.get_datatype_size(datatype, 3)

    e = event.CommEvent("Recv", state.rank, source, tag)
    generator.add_call_event(context, e)

    request_ids = (state.add_recv_request(source, tag, buf_ptr, size),)
    if status_ptr:
        status_ptrs = [ status_ptr ]
    else:
        status_ptrs = None
    state.set_wait(request_ids, status_ptrs)
    # TODO: Optimization : If message is already here,
    # then non block and continue
    return True

def MPI_ISend(generator, args, gstate, state, context):
    buf_ptr, count, datatype, target, tag, comm, request_ptr = \
        convert_types(args,
                      ("ptr", # buf_ptr
                       "int", # count
                       "int", # datatype
                       "int", # target
                       "int", # tag
                       "int", # comm
                       "ptr", # request_ptr
                      ))
    generator.validate_count(count, 2)
    generator.validate_rank(target, 4, False)
    generator.validate_tag(tag, 5, False)

    size = count * generator.get_datatype_size(datatype, 3)

    buffer_id, hash = generator.controller.new_buffer(buf_ptr, size, hash=True)
    vg_buffer = generator.vg_buffers.new(buffer_id)
    message = gstate.get_state(target).add_message(
            state.rank, target, tag, vg_buffer, size, hash)
    request_id = generator.make_send_request(gstate, state, message)
    generator.controller.write_int(request_ptr, request_id)

    e = event.CommEvent("Isend", state.rank, target, tag, request_id)
    generator.add_call_event(context, e)
    return False

def MPI_IRecv(generator, args, gstate, state, context):
    buf_ptr, count, datatype, source, tag, comm, request_ptr = \
        convert_types(args,
                      ("ptr", # buf_ptr
                       "int", # count
                       "int", # datatype
                       "int", # source
                       "int", # tag
                       "int", # comm
                       "ptr", # request_ptr
                      ))

    generator.validate_count(count, 2)
    generator.validate_rank(source, 4, True)
    generator.validate_tag(tag, 5, True)

    size = count * generator.get_datatype_size(datatype, 3)

    request_id = state.add_recv_request(source, tag, buf_ptr, size)
    generator.controller.write_int(request_ptr, request_id)

    e = event.CommEvent("Irecv", state.rank, source, tag, request_id)
    generator.add_call_event(context, e)
    return False

def MPI_Wait(generator, args, gstate, state, context):
    request_ptr, status_ptr = args
    request_ids = [ generator.controller.read_int(request_ptr) ]
    if status_ptr != "0":
        status_ptrs = [ status_ptr ]
    else:
        status_ptrs = None
    generator.validate_request_ids(state, request_ids)
    state.set_wait(request_ids, status_ptrs)

    e = event.WaitEvent("Wait", state.rank, request_ids)
    generator.add_call_event(context, e)
    return True

def MPI_Test(generator, args, gstate, state, context):
    request_ptr, flag_ptr, status_ptr = args
    request_ids = [ generator.controller.read_int(request_ptr) ]
    generator.validate_request_ids(state, request_ids)
    state.set_test(request_ids, flag_ptr)

    e = event.WaitEvent("Test", state.rank, request_ids)
    generator.add_call_event(context, e)
    return True

def MPI_Waitall(generator, args, gstate, state, context):
    count, requests_ptr, status_ptr = args
    count = int(count)
    request_ids = generator.controller.read_ints(requests_ptr, count)
    if status_ptr != "0":
        status_ptr = int(status_ptr)
        status_ptrs = [ status_ptr + i * POINTER_SIZE for i in xrange(count) ]
    else:
        status_ptrs = None

    generator.validate_request_ids(state, request_ids)
    state.set_wait(request_ids, status_ptrs)

    e = event.WaitEvent("Waitall", state.rank, request_ids)
    generator.add_call_event(context, e)
    return True

def MPI_Barrier(generator, args, gstate, state, context):
    args = convert_types(args, ("int",))
    return call_collective_operation(generator,
                                     gstate,
                                     state,
                                     context,
                                     collectives.Barrier,
                                     True,
                                     args)

def MPI_Gather(generator, args, gstate, state, context):
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
                                     gstate,
                                     state,
                                     context,
                                     collectives.Gather,
                                     True,
                                     args)

def MPI_Gatherv(generator, args, gstate, state, context):
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
                                     gstate,
                                     state,
                                     context,
                                     collectives.Gatherv,
                                     True,
                                     args)

def MPI_Scatter(generator, args, gstate, state, context):
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
                                     gstate,
                                     state,
                                     context,
                                     collectives.Scatter,
                                     True,
                                     args)

def MPI_Scatterv(generator, args, gstate, state, context):
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
                                     gstate,
                                     state,
                                     context,
                                     collectives.Scatterv,
                                     True,
                                     args)

def MPI_Reduce(generator, args, gstate, state, context):
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
                                     gstate,
                                     state,
                                     context,
                                     collectives.Reduce,
                                     True,
                                     args)

def MPI_Allreduce(generator, args, gstate, state, context):
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
                                     gstate,
                                     state,
                                     context,
                                     collectives.AllReduce,
                                     True,
                                     args)

def MPI_Ibarrier(generator, args, gstate, state, context):
    args = convert_types(args, ("int", "ptr"))
    return call_collective_operation(generator,
                                     gstate,
                                     state,
                                     context,
                                     collectives.Barrier,
                                     False,
                                     args)

def MPI_Igather(generator, args, gstate, state, context):
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
                                     gstate,
                                     state,
                                     context,
                                     collectives.Gather,
                                     False,
                                     args)

def MPI_Igatherv(generator, args, gstate, state, context):
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
                                     gstate,
                                     state,
                                     context,
                                     collectives.Gatherv,
                                     False,
                                     args)

def MPI_Iscatter(generator, args, gstate, state, context):
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
                                     gstate,
                                     state,
                                     context,
                                     collectives.Scatter,
                                     False,
                                     args)

def MPI_Iscatterv(generator, args, gstate, state, context):
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
                                     gstate,
                                     state,
                                     context,
                                     collectives.Scatterv,
                                     False,
                                     args)

def MPI_Ireduce(generator, args, gstate, state, context):
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
                                     gstate,
                                     state,
                                     context,
                                     collectives.Reduce,
                                     False,
                                     args)

def MPI_Iallreduce(generator, args, gstate, state, context):
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
                                     gstate,
                                     state,
                                     context,
                                     collectives.AllReduce,
                                     False,
                                     args)


def call_collective_operation(generator,
                              gstate,
                              state,
                              context,
                              op_class,
                              blocking,
                              args):
    if not blocking:
        request_ptr = args[-1]
        args = args[:-1]
    op = gstate.call_collective_operation(
                generator, state, op_class, blocking, args)
    request_id = state.add_collective_request(op.cc_id)
    if blocking:
        state.set_wait((request_id,))
    else:
        generator.controller.write_int(request_ptr, request_id)
    generator.add_call_event(context, op.get_event(state))
    return blocking

calls = {
        "MPI_Comm_rank" : MPI_Comm_rank,
        "MPI_Comm_size" : MPI_Comm_size,
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
        "MPI_Allreduce" : MPI_Allreduce,
        "MPI_Ibarrier" : MPI_Ibarrier,
        "MPI_Igather" : MPI_Igather,
        "MPI_Igatherv" : MPI_Igatherv,
        "MPI_Iscatter" : MPI_Iscatter,
        "MPI_Iscatterv" : MPI_Iscatterv,
        "MPI_Ireduce" : MPI_Ireduce,
        "MPI_Iallreduce" : MPI_Iallreduce,
}
