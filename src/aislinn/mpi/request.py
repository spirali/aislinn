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

    def __init__(self, request_id):
        self.id = request_id

    def is_send(self):
        return False

    def is_receive(self):
        return False

    def is_collective(self):
        return False

    def is_deterministic(self):
        return True

    def compute_hash(self, hashthread):
        hashthread.update(str(self.id))

    def inc_ref(self):
        pass

    def dec_ref(self):
        pass

    def transfer(self, transfer_context):
        request = transfer_context.translate_table.get(self)
        if request is not None:
            return request
        request = copy.copy(self)
        transfer_context.set_translate(self, request)
        return request

    def is_send_recv_not_proc_null(self):
        return False


class SendRequest(Request):

    name = "send"

    def __init__(self, request_id, send_type,
                 comm, target, tag, data_ptr, datatype, count):
        Request.__init__(self, request_id)
        self.send_type = send_type
        self.comm = comm
        self.target = target
        self.tag = tag
        self.data_ptr = data_ptr
        self.datatype = datatype
        self.count = count
        self.vg_buffer = None

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
        gcontext.generator.message_sizes.add(sz)

    def inc_ref(self):
        if self.vg_buffer:
            self.vg_buffer.inc_ref()

    def dec_ref(self):
        if self.vg_buffer:
            self.vg_buffer.dec_ref()

    def transfer(self, transfer_context):
        request = transfer_context.translate_table.get(self)
        if request is not None:
            request.inc_ref()
            return request
        request = Request.transfer(self, transfer_context)
        if request.vg_buffer:
            request.vg_buffer = \
                transfer_context.transfer_buffer(self.vg_buffer)
        return request

    def is_standard_send(self):
        return self.send_type == SendRequest.Standard

    def is_send(self):
        return True

    def compute_hash(self, hashthread):
        Request.compute_hash(self, hashthread)
        hashthread.update("SR {0}".format(self.send_type))
        if self.vg_buffer:
            hashthread.update(self.vg_buffer.hash)

    def is_data_addr(self, addr):
        sz = self.count * self.datatype.size
        return addr >= self.data_ptr and addr < self.data_ptr + sz

    def __repr__(self):
        return "<SendRqst {0:x} id={1} type={2} comm_id={3} target={4} tag={5}>" \
            .format(id(self), self.id, self.send_type,
                    self.comm.comm_id, self.target, self.tag)


class ReceiveRequest(Request):

    name = "receive"

    def __init__(self, request_id, comm, source, tag,
                 data_ptr, datatype, count):
        Request.__init__(self, request_id)
        self.comm = comm
        self.source = source
        self.tag = tag
        self.data_ptr = data_ptr
        self.datatype = datatype
        self.count = count
        self.vg_buffer = None
        self.source_rank = None
        self.source_tag = None

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

    def transfer(self, transfer_context):
        request = transfer_context.translate_table.get(self)
        if request is not None:
            request.inc_ref()
            return request
        request = Request.transfer(self, transfer_context)
        if request.vg_buffer:
            request.vg_buffer = \
                transfer_context.transfer_buffer(self.vg_buffer)
        return request

    def is_receive(self):
        return True

    def compute_hash(self, hashthread):
        Request.compute_hash(self, hashthread)
        hashthread.update(
            "RR {0.comm.comm_id} {0.source} {0.tag} "
            "{0.data_ptr} {0.datatype.type_id} {0.count}".format(self))
        if self.vg_buffer:
            hashthread.update(self.vg_buffer.hash)

    def is_deterministic(self):
        return self.source != consts.MPI_ANY_SOURCE

    def is_data_addr(self, addr):
        sz = self.count * self.datatype.size
        return addr >= self.data_ptr and addr < self.data_ptr + sz

    def __repr__(self):
        return "<RecvRqst {1:x} id={0.id} source={0.source}, " \
            "tag={0.tag}, data_ptr={0.data_ptr:x}>" \
            .format(self, id(self))


class CollectiveRequest(Request):

    name = "collective"

    def __init__(self, request_id, comm, cc_id):
        Request.__init__(self, request_id)
        self.cc_id = cc_id
        self.comm = comm

    def is_collective(self):
        return True

    def compute_hash(self, hashthread):
        Request.compute_hash(self, hashthread)
        hashthread.update("CR {0} {1}".format(self.comm.comm_id, self.cc_id))

    def is_data_addr(self, addr):
        # TODO: Implement this method
        return False

    def __repr__(self):
        return "<CCRqst comm_id={0.comm.comm_id} cc_id={0.cc_id}>".format(self)
