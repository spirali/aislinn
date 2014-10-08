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
        errormsg.InvalidArgument(op,
                                 arg_position,
                                 "Invalid operation").throw()
    return op

def check_rank(comm,
               rank,
               arg_position,
               any_source_allowed=False,
               proc_null_allowed=False):

    if rank == consts.MPI_PROC_NULL:
        if not proc_null_allowed:
            errormsg.InvalidArgument("MPI_PROC_NULL",
                                     arg_position,
                                     "MPI_PROC_NULL not allowed").throw()
    elif rank == consts.MPI_ANY_SOURCE:
        if not any_source_allowed:
            errormsg.InvalidArgument("MPI_ANY_SOURCE",
                                     arg_position,
                                     "MPI_ANY_SOURCE not allowed").throw()
    elif rank < 0 or rank >= comm.group.size:
        errormsg.InvalidArgument(rank, arg_position, "Invalid rank").throw()
    return rank

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
    return tag

def check_count(count, arg_position):
    if count < 0:
        errormsg.InvalidArgument(count,
                                 arg_position,
                                 "Count has to be non-negative.").throw()
    return count

def check_size(size, arg_position):
    if size < 0:
        errormsg.InvalidArgument(size,
                                 arg_position,
                                 "Size has to be non-negative.").throw()

def check_sizes(sizes, arg_position):
    for i, size in enumerate(sizes):
        if size < 0:
            errormsg.InvalidArgument(size,
                                     arg_position,
                                     "Size has to be non-negative. "
                                     "({0}. item of array)".format(i)
                                     ).throw()

def check_color(color, arg_position):
    if color != consts.MPI_UNDEFINED and color < 0:
        errormsg.InvalidArgument(color,
                                 arg_position,
                                 "Color has to be non-negative.").throw()

def check_datatype(state, type_id, arg_position, allow_uncommited=False):
    datatype = state.get_datatype(type_id)
    if datatype is None:
        errormsg.InvalidArgument(type_id,
                                 arg_position,
                                 "Invalid datatype").throw()
    if not datatype.commited and not allow_uncommited:
        e = errormsg.CallError()
        e.name = "uncommited"
        e.short_description = "Uncommited datatype"
        e.description = "Uncommited datatype used in communication"
        e.throw()
    return datatype

def check_datatypes(state, type_ids, arg_position, allow_uncommited=False):
    return [ check_datatype(state, type_id, arg_position, allow_uncommited)
             for type_id in type_ids ]

def check_comm(state, comm_id, arg_position):
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

def check_and_get_group(state, group_id, arg_position):
    group = state.get_group(group_id)
    if group is None:
        errormsg.InvalidArgument(group_id,
                                 arg_position,
                                 "Invalid group").throw()
    return group

def check_request_id(state, request_id):
    if request_id == consts.MPI_REQUEST_NULL:
        errormsg.InvalidArgument("MPI_REQUEST_NULL",
                                 None,
                                 "Invalid request").throw()
    request = state.get_request(request_id)

    if request is None:
        errormsg.InvalidArgument(request_id, None, "Invalid request").throw()

def check_persistent_request(state, request_id, inactive):
    if request_id == consts.MPI_REQUEST_NULL:
        errormsg.InvalidArgument("MPI_REQUEST_NULL",
                                 None,
                                 "Invalid request").throw()
    request = state.get_persistent_request(request_id)

    if request is None:
        errormsg.InvalidArgument(
                request_id, None, "Invalid persistent request").throw()

    if inactive and state.get_request(request_id) is not None:
        errormsg.InvalidArgument(
                request_id, None, "Persistent request is active").throw()
    return request

def check_request_ids(state, request_ids):
    for request_id in request_ids:
        check_request_id(state, request_id)
