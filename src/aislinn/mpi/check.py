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

import errormsg
import consts

def check_rank(context,
               comm,
               rank,
               arg_position,
               any_source_allowed=False,
               proc_null_allowed=False):
    return check_rank_in_group(context,
                               comm.group,
                               rank,
                               arg_position,
                               any_source_allowed,
                               proc_null_allowed)



def check_rank_in_group(
               context,
               group,
               rank,
               arg_position,
               any_source_allowed=False,
               proc_null_allowed=False):

    if rank == consts.MPI_PROC_NULL:
        if not proc_null_allowed:
            context.add_error_and_throw(
                errormsg.InvalidRank(context,
                                     value=rank,
                                     arg_position=arg_position))
    elif rank == consts.MPI_ANY_SOURCE:
        if not any_source_allowed:
            context.add_error_and_throw(
                errormsg.InvalidRank(context,
                                     value=rank,
                                     arg_position=arg_position))
    elif rank < 0 or rank >= group.size:
        context.add_error_and_throw(
                errormsg.InvalidRank(context,
                                     value=rank,
                                     arg_position=arg_position))
    return rank

def check_tag(context,
              tag,
              arg_position,
              any_tag_allowed):

    if (tag == consts.MPI_ANY_TAG and any_tag_allowed) or tag >= 0:
        return tag
    context.add_error_and_throw(
        errormsg.InvalidTag(context, value=tag, arg_position=arg_position))

def check_count(context, count, arg_position):
    if count >= 0:
        return count
    context.add_error_and_throw(
        errormsg.InvalidCount(context, value=count, arg_position=arg_position))

def check_sizes(context, sizes, arg_position):
    for i, size in enumerate(sizes):
        if size < 0:
            context.add_error_and_throw(errormsg.InvalidLength(
                        context, value=size, arg_position=arg_position, index=i))

def check_color(context, color, arg_position):
    if color != consts.MPI_UNDEFINED and color < 0:
        context.add_error_and_throw(
            errormsg.InvalidColor(
                context, value=color, arg_position=arg_position))

def check_op(context, op_id, arg_position):
    if op_id == consts.MPI_OP_NULL:
        context.add_error_and_throw(
                errormsg.InvalidOperation(context,
                                          value=op_id,
                                          arg_position=arg_position))
    op = context.state.get_op(op_id)
    if op is None:
        context.add_error_and_throw(
                errormsg.InvalidOperation(context,
                                          value=op_id,
                                          arg_position=arg_position))
    return op

def check_datatype(context, type_id, arg_position, allow_uncommited=False):
    datatype = context.state.get_datatype(type_id)
    if datatype is None:
        context.add_error_and_throw(
            errormsg.InvalidDatatype(
                context, value=type_id, arg_position=arg_position))
    if not datatype.commited and not allow_uncommited:
        context.add_error_and_throw(
            errormsg.UncommitedDatatype(
                context, value=type_id, arg_position=arg_position))
    return datatype

def check_datatypes(context, type_ids, arg_position, allow_uncommited=False):
    return [ check_datatype(context, type_id, arg_position, allow_uncommited)
             for type_id in type_ids ]

def check_comm(context, comm_id, arg_position):
    if comm_id == consts.MPI_COMM_NULL:
        context.add_error_and_throw(
                errormsg.InvalidCommunicator(context,
                value=comm_id,
                arg_position=arg_position))
    comm = context.state.get_comm(comm_id)
    if comm is None:
        context.add_error_and_throw(
                errormsg.InvalidCommunicator(context,
                value=comm_id,
                arg_position=arg_position))
    return comm

def check_and_get_group(context, group_id, arg_position):
    group = context.state.get_group(group_id)
    if group is None:
        context.add_error_and_throw(errormsg.InvalidGroup(
            context, value=group_id, arg_position=arg_position))
    return group

def check_request_id(context, request_id, arg_position, index=None):
    if request_id == consts.MPI_REQUEST_NULL:
        return
    request = context.state.get_request(request_id)

    if request is None:
        context.add_error_and_throw(errormsg.InvalidRequest(
            context, value=request_id, arg_position=arg_position, index=index))

def check_persistent_request(
        context, request_id, inactive, arg_position, index=None):
    if request_id == consts.MPI_REQUEST_NULL:
        context.add_error_and_throw(errormsg.InvalidPersistentRequest(
            context, value=request_id, arg_position=arg_position, index=index))
    request = context.state.get_persistent_request(request_id)

    if request is None:
        context.add_error_and_throw(errormsg.NotPersistentRequest(
            context, value=request_id, arg_position=arg_position, index=index))

    if inactive and context.state.get_request(request_id) is not None:
        context.add_error_and_throw(errormsg.ActivePersistentRequest(
            context, value=request_id, arg_position=arg_position, index=index))
    return request

def check_unique_values(context, items, arg_position):
    if len(set(items)) != len(items):
        e = errormsg.NonUniqueValues(
                context,
                value=items,
                arg_position=arg_position)
        context.add_error_and_throw(e)

def check_request_ids(context, request_ids, arg_position):
    for i, request_id in enumerate(request_ids):
        check_request_id(context, request_id, arg_position, i)

def check_keyval(context, keyval_id, arg_position):
    keyval = context.state.get_keyval(keyval_id)
    if keyval is None:
        context.add_error_and_throw(errormsg.InvalidKeyval(
            context, value=keyval_id, arg_position=arg_position))
    return keyval
