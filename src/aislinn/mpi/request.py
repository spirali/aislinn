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
import copy
from message import Message

class Request(EqMixin):

    pointer = None
    status_ptr = None

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
        hashthread.update(
                "R {0} {1} {2} ".format(self.id,
                                        self.pointer,
                                        self.status_ptr))

    def reinit(self):
        if self.pointer is None and self.status_ptr is None:
            return self
        request = copy.copy(self)
        request.pointer = None
        request.status_ptr = None
        return request


class SendRequest(Request):

    Standard = 0
    Synchronous = 1
    Buffered = 2

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

    def create_message(self, generator, state):
        assert self.message is None
        sz = self.count * self.datatype.size
        vg_buffer = generator.new_buffer_and_pack(self.datatype,
                                                  self.count,
                                                  self.data_ptr)
        comm = state.get_comm(self.comm_id)
        target_pid = comm.group.rank_to_pid(self.target)
        message = Message(comm.comm_id, state.get_rank(comm),
                          self.target, self.tag, vg_buffer, sz)
        state.gstate.get_state(target_pid).add_message(message)
        generator.message_sizes.add(sz)
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

    def __repr__(self):
        return "<SendRequest {0}>".format(self.send_type)


class ReceiveRequest(Request):

    def __init__(self, request_id, comm_id, source, tag, data_ptr, datatype, count):
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

    def __repr__(self):
        return "<RecvRequst {1:x} source={0.source}, tag={0.tag}>" \
                .format(self, id(self))


class CompletedRequest(Request):

    def __init__(self, request_id, original_request):
        Request.__init__(self, request_id)
        self.original_request = original_request

    def compute_hash(self, hashthread):
        Request.compute_hash(self, hashthread)
        hashthread.update("CR ")

    def is_completed(self):
        return True


class CollectiveRequest(Request):

    def __init__(self, request_id, comm_id, cc_id):
        Request.__init__(self, request_id)
        self.cc_id = cc_id
        self.comm_id = comm_id

    def is_collective(self):
        return True

    def compute_hash(self, hashthread):
        Request.compute_hash(self, hashthread)
        hashthread.update("CR {0} {0}".format(self.comm_id, self.cc_id))

    def __repr__(self):
        return "CCOP(comm_id={0.comm_id} cc_id={0.cc_id})".format(self)
