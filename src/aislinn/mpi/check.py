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
import errormsg
import consts

def check_op(op,
                arg_position):
    if not types.is_valid_op(op):
        errormsg.InvalidArgument(op, arg_position).throw()

def check_rank(comm,
               rank,
               arg_position,
               any_source_allowed=False):

    if rank == consts.MPI_ANY_SOURCE:
        if not any_source_allowed:
            errormsg.InvalidArgument("MPI_ANY_SOURCE",
                                     arg_position,
                                     "MPI_ANY_SOURCE not allowed").throw()
    elif rank < 0 or rank >= comm.group.size:
        errormsg.InvalidArgument(rank, arg_position, "Invalid rank").throw()

def check_tag(tag,
              arg_position,
              any_tag_allowed):

    if tag == consts.MPI_ANY_TAG:
        if not any_tag_allowed:
            errormsg.InvalidArgument("MPI_ANY_TAG", arg_position).throw()
    elif tag < 0:
        errormsg.InvalidArgument(
                tag,
                arg_position,
                "Tag has to be a non-negative number.").throw()

def check_count(size, arg_position):
    if size < 0:
        errormsg.InvalidArgument(size,
                                 arg_position,
                                 "Count has to be non-negative.").throw()

def check_color(color, arg_position):
    if color != consts.MPI_UNDEFINED and color < 0:
        errormsg.InvalidArgument(color,
                                 arg_position,
                                 "Color has to be non-negative.").throw()

def check_datatype(state, type_id, arg_position):
    datatype = state.get_datatype(type_id)
    if datatype is None:
        errormsg.InvalidArgument(datatype, arg_position).throw()
    return datatype

def check_and_get_comm(state, comm_id, arg_position):
    if comm_id == consts.MPI_COMM_NULL:
        errormsg.InvalidArgument("MPI_COMM_NULL",
                                 arg_position,
                                 "Invalid communicator").throw()
    comm = state.get_comm(comm_id)
    if comm is None:
        errormsg.InvalidArgument(comm_id,
                                 arg_position,
                                 "Invalid communicator").throw()
    return comm

def check_request_ids(state, request_ids):
    for request_id in request_ids:
        if not state.is_request_id_valid(request_id):
            raise Exception("Invalid request id {0}, pid {1} ({2})"
                    .format(request_id, state.pid, state.requests))
