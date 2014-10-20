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


import consts

class Operation(object):

    def compute_hash(self, hashthread):
        hashthread.update("Op {0} {1} {2} ".
                format(self.op_id,
                       self.commute,
                       self.fn_ptr))

class UserDefinedOperation(Operation):
    buildin = False

    def __init__(self, commute, fn_ptr):
        self.op_id = None
        self.commute = commute
        self.fn_ptr = fn_ptr

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
    BuildinOperation(consts.MPI_MINLOC, "MPI_MINLOC"),
    BuildinOperation(consts.MPI_MAXLOC, "MPI_MAXLOC"),
    ])
