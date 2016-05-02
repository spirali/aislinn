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


import consts


class Operation(object):
    pass


class UserDefinedOperation(Operation):
    buildin = False

    def __init__(self, commute, fn_ptr):
        self.op_id = None
        self.commute = commute
        self.fn_ptr = fn_ptr

    def serialize_to_list(self, lst):
        lst.append(self.op_id)
        lst.append(self.commute)
        lst.append(self.fn_ptr)

    @classmethod
    def deserialize_from_list(cls, loader):
        op_id = loader.get()
        op = UserDefinedOperation(loader.get(), loader.get())
        op.op_id = op_id
        return op


class BuildinOperation(Operation):
    buildin = True

    def __init__(self, op_id, name):
        self.op_id = op_id
        self.commute = True
        self.fn_ptr = None
        self.name = name


buildin_operations = dict((o.op_id, o) for o in [
    BuildinOperation(consts.MPI_SUM, "MPI_SUM"),
    BuildinOperation(consts.MPI_PROD, "MPI_PROD"),
    BuildinOperation(consts.MPI_MIN, "MPI_MIN"),
    BuildinOperation(consts.MPI_MAX, "MPI_MAX"),
    BuildinOperation(consts.MPI_LAND, "MPI_LAND"),
    BuildinOperation(consts.MPI_LOR, "MPI_LOR"),
    BuildinOperation(consts.MPI_BAND, "MPI_BAND"),
    BuildinOperation(consts.MPI_BOR, "MPI_BOR"),
    BuildinOperation(consts.MPI_MINLOC, "MPI_MINLOC"),
    BuildinOperation(consts.MPI_MAXLOC, "MPI_MAXLOC"),
    ])
