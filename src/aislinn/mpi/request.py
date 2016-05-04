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


from base.utils import EqMixin
import consts

import copy


class Request(EqMixin):

    TYPE_RECEIVE = 0
    TYPE_SEND_STD = 1  # Standard send
    TYPE_SEND_EAGER = 2  # BSEND
    TYPE_SEND_RENDEZVOUS = 3  # SSEND
    TYPE_COLLECTIVE = 4
    TYPES_COUNT = 5

    stacktrace = None

    def __init__(self, request_id, comm):
        self.id = request_id
        self.comm = comm

    def serialize_to_list(self, lst):
        lst.append(self.name)
        lst.append(self.id)
        lst.append(self.comm.comm_id)
        lst.append(self.stacktrace)

    def is_send(self):
        return False

    def is_receive(self):
        return False

    def is_collective(self):
        return False

    def is_deterministic(self):
        return True

    def inc_ref(self):
        pass

    def dec_ref(self):
        pass

    def is_send_recv_not_proc_null(self):
        return False


class SendRequest(Request):

    name = "send"

    def __init__(self, request_id, send_type,
                 comm, target, tag, data_ptr, datatype, count, vg_buffer=None):
        Request.__init__(self, request_id, comm)
        self.send_type = send_type
        self.target = target
        self.tag = tag
        self.data_ptr = data_ptr
        self.datatype = datatype
        self.count = count
        self.vg_buffer = vg_buffer

    def is_send_recv_not_proc_null(self):
        return self.target != consts.MPI_PROC_NULL

    def create_message(self, context):
        assert self.vg_buffer is None
        if self.target == consts.MPI_PROC_NULL:
            return
        sz = self.count * self.datatype.size
        target_pid = self.comm.group.rank_to_pid(self.target)
        self.vg_buffer = context.make_buffer_for_one(
            target_pid, self.data_ptr, self.datatype, self.count)
        gcontext = context.gcontext
        gcontext.worker.message_sizes.add(sz)

    def inc_ref(self):
        if self.vg_buffer:
            self.vg_buffer.inc_ref()

    def dec_ref(self):
        if self.vg_buffer:
            self.vg_buffer.dec_ref()

    def collect_buffers(self, lst):
        if self.vg_buffer:
            lst.append(self.vg_buffer)

    def is_standard_send(self):
        return self.send_type == SendRequest.Standard

    def is_send(self):
        return True

    def serialize_to_list(self, lst):
        Request.serialize_to_list(self, lst)
        lst.append(self.send_type)
        lst.append(self.target)
        lst.append(self.tag)
        lst.append(self.data_ptr)
        lst.append(self.datatype.type_id)
        lst.append(self.count)
        if self.vg_buffer:
            lst.append(self.vg_buffer.hash)
        else:
            lst.append(None)

    def is_data_addr(self, addr):
        sz = self.count * self.datatype.size
        return addr >= self.data_ptr and addr < self.data_ptr + sz

    def __repr__(self):
        return "<SendRqst {0:x} id={1} type={2} comm_id={3} target={4} tag={5} {6}>" \
            .format(id(self), self.id, self.send_type,
                    self.comm.comm_id, self.target, self.tag, self.vg_buffer)


class ReceiveRequest(Request):

    name = "receive"

    def __init__(self, request_id, comm, source, tag,
                 data_ptr, datatype, count):
        Request.__init__(self, request_id, comm)
        self.source = source
        self.tag = tag
        self.data_ptr = data_ptr
        self.datatype = datatype
        self.count = count
        self.vg_buffer = None
        self.source_rank = None
        self.source_tag = None

    def serialize_to_list(self, lst):
        Request.serialize_to_list(self, lst)
        lst.append(self.source)
        lst.append(self.tag)
        lst.append(self.data_ptr)
        lst.append(self.datatype.type_id)
        lst.append(self.count)
        if self.vg_buffer:
            lst.append(self.vg_buffer.hash)
        else:
            lst.append(None)
        lst.append(self.source_rank)
        lst.append(self.source_tag)

    def is_send_recv_not_proc_null(self):
        return self.source != consts.MPI_PROC_NULL

    def make_finished_request(self, rank, tag, vg_buffer):
        assert self.vg_buffer is None
        r = copy.copy(self)
        vg_buffer.inc_ref()
        r.vg_buffer = vg_buffer
        r.source_rank = rank
        r.source_tag = tag
        return r

    def is_suppressed_by(self, r):
        return (self.source == r.source or r.source == consts.MPI_ANY_SOURCE) \
            and (self.tag == r.tag or r.tag == consts.MPI_ANY_TAG) and \
            (self.comm.comm_id == r.comm.comm_id)

    def inc_ref(self):
        if self.vg_buffer:
            self.vg_buffer.inc_ref()

    def dec_ref(self):
        if self.vg_buffer:
            self.vg_buffer.dec_ref()

    def collect_buffers(self, lst):
        if self.vg_buffer:
            lst.append(self.vg_buffer)

    def is_receive(self):
        return True

    def is_deterministic(self):
        return self.source != consts.MPI_ANY_SOURCE

    def is_data_addr(self, addr):
        sz = self.count * self.datatype.size
        return addr >= self.data_ptr and addr < self.data_ptr + sz

    def __repr__(self):
        return "<RecvRqst {1:x} id={0.id} source={0.source}, " \
            "tag={0.tag}, data_ptr={0.data_ptr:x} {0.vg_buffer}>" \
            .format(self, id(self))


class CollectiveRequest(Request):

    name = "collective"

    def __init__(self, request_id, comm, cc_id):
        Request.__init__(self, request_id, comm)
        self.cc_id = cc_id

    def serialize_to_list(self, lst):
        Request.serialize_to_list(self, lst)
        lst.append(self.cc_id)

    def is_collective(self):
        return True

    def is_data_addr(self, addr):
        # TODO: Implement this method
        return False

    def __repr__(self):
        return "<CCRqst comm_id={0.comm.comm_id} cc_id={0.cc_id}>".format(self)


def load_request(loader, state):
    name = loader.get()
    request_id = loader.get()
    comm = state.get_comm(loader.get())
    stacktrace = loader.get()
    if name == "send":
        request = SendRequest(request_id,
                              loader.get(),
                              comm,
                              loader.get(),
                              loader.get(),
                              loader.get(),
                              state.get_datatype(loader.get()),
                              loader.get(),
                              loader.get_object())
        if request.vg_buffer:
            request.vg_buffer.inc_ref()
    elif name == "receive":
        request = ReceiveRequest(request_id,
                                 comm,
                                 loader.get(),
                                 loader.get(),
                                 loader.get(),
                                 state.get_datatype(loader.get()),
                                 loader.get())
        request.vg_buffer = loader.get_object()
        if request.vg_buffer:
            request.vg_buffer.inc_ref()
        request.source_rank = loader.get()
        request.source_tag = loader.get()
    elif name == "collective":
        request = CollectiveRequest(request_id, comm, loader.get())
    else:
        raise Exception("Unknown request type: " + repr(name))

    if request is not None:
        request.stacktrace = stacktrace
    return request
