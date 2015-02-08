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


from base.utils import EqMixin
import consts
from message import Message

class Request(EqMixin):

    stacktrace = None

    def __init__(self, request_id):
        self.id = request_id

    def is_send(self):
        return False

    def is_receive(self):
        return False

    def is_completed(self):
        return False

    def is_collective(self):
        return False

    def is_deterministic(self):
        return True

    def compute_hash(self, hashthread):
        hashthread.update(str(self.id))


class SendRequest(Request):

    Standard = 0
    Synchronous = 1
    Buffered = 2

    name = "send"

    def __init__(self, request_id, send_type,
                 comm_id, target, tag, data_ptr, datatype, count):
        assert send_type >= 0 and send_type <= 2
        Request.__init__(self, request_id)
        self.send_type = send_type
        self.comm_id = comm_id
        self.target = target
        self.tag = tag
        self.data_ptr = data_ptr
        self.datatype = datatype
        self.count = count
        self.message = None

    def create_message(self, context):
        assert self.message is None
        if self.target == consts.MPI_PROC_NULL:
            return
        sz = self.count * self.datatype.size
        vg_buffer = context.generator.new_buffer_and_pack(context.controller,
                                                          self.datatype,
                                                          self.count,
                                                          self.data_ptr)

        comm = context.state.get_comm(self.comm_id)
        target_pid = comm.group.rank_to_pid(self.target)
        message = Message(comm.comm_id, context.state.get_rank(comm),
                          self.target, self.tag, vg_buffer, sz)
        context.gstate.get_state(target_pid).add_message(message)
        context.generator.message_sizes.add(sz)
        self.message = message

    def is_standard_send(self):
        return self.send_type == SendRequest.Standard

    def is_send(self):
        return True

    def compute_hash(self, hashthread):
        Request.compute_hash(self, hashthread)
        hashthread.update("SR {0}".format(self.send_type))
        if self.message:
            self.message.compute_hash(hashthread)

    def is_data_addr(self, addr):
        sz = self.count * self.datatype.size
        return addr >= self.data_ptr and addr < self.data_ptr + sz

    def __repr__(self):
        return "<SendRqst id={0} type={1} target={2} tag={3}>" \
                .format(self.id, self.send_type, self.target, self.tag)


class ReceiveRequest(Request):

    name = "receive"

    def __init__(self, request_id, comm_id, source, tag,
                 data_ptr, datatype, count):
        Request.__init__(self, request_id)
        self.comm_id = comm_id
        self.source = source
        self.tag = tag
        self.data_ptr = data_ptr
        self.datatype = datatype
        self.count = count

    def is_receive(self):
        return True

    def compute_hash(self, hashthread):
        Request.compute_hash(self, hashthread)
        hashthread.update(
                "RR {0.comm_id} {0.source} {0.tag} "
                "{0.data_ptr} {0.datatype.type_id} {0.count}".format(self))

    def is_deterministic(self):
        return self.source != consts.MPI_ANY_SOURCE

    def is_data_addr(self, addr):
        sz = self.count * self.datatype.size
        return addr >= self.data_ptr and addr < self.data_ptr + sz

    def __repr__(self):
        return "<RecvRqst {1:x} id={0.id} source={0.source}, " \
               "tag={0.tag}, data_ptr={0.data_ptr:x}>" \
                .format(self, id(self))


class CompletedRequest(Request):

    name = "completed"

    def __init__(self, request_id, original_request, message=None):
        Request.__init__(self, request_id)
        assert not original_request.is_completed()
        self.original_request = original_request
        self.message = message
        if original_request.stacktrace:
            self.stacktrace = original_request.stacktrace

    def compute_hash(self, hashthread):
        Request.compute_hash(self, hashthread)
        hashthread.update("CR ")

    def is_completed(self):
        return True

    def is_data_addr(self, addr):
        return self.original_request.is_data_addr(addr)

    def __repr__(self):
        return "<CompleteRqst {0:x} {1} {2}>" \
                .format(id(self), self.id, repr(self.original_request))


class CollectiveRequest(Request):

    name = "collective"

    def __init__(self, request_id, comm_id, cc_id):
        Request.__init__(self, request_id)
        self.cc_id = cc_id
        self.comm_id = comm_id

    def is_collective(self):
        return True

    def compute_hash(self, hashthread):
        Request.compute_hash(self, hashthread)
        hashthread.update("CR {0} {0}".format(self.comm_id, self.cc_id))

    def is_data_addr(self, addr):
        # TODO: Implement this method
        return False

    def __repr__(self):
        return "<CCRqst comm_id={0.comm_id} cc_id={0.cc_id}>".format(self)
