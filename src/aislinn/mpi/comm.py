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
import base.utils

class Communicator:

    def __init__(self, comm_id, group):
        self.comm_id = comm_id
        self.group = group

    def compute_hash(self, hashthread):
        hashthread.update(str(self.comm_id))
        hashthread.update(str(self.group.table))


class Group(base.utils.EqMixin):

    def __init__(self, table):
        self.table = table

    @property
    def size(self):
        return len(self.table)

    @property
    def ranks(self):
        return range(self.size)

    def is_valid_rank(self, rank):
        return rank >= 0 and rank < len(self.table)

    def rank_to_pid(self, rank):
        return self.table[rank]

    def pid_to_rank(self, pid):
        try:
            return self.table.index(pid)
        except ValueError:
            return None

    def pids(self):
        return self.table

def comm_compare(comm1, comm2):
    if comm1 is comm2:
        return consts.MPI_IDENT
    if comm1.group.table == comm2.group.table:
        return consts.MPI_CONGRUENT
    if set(comm1.group.table) == set(comm2.group.table):
        return consts.MPI_SIMILAR
    return consts.MPI_UNEQUAL

def group_compare(group1, group2):
    if group1.table == group2.table:
        return consts.MPI_IDENT
    if set(group1.table) == set(group2.table):
        return consts.MPI_SIMILAR
    return consts.MPI_UNEQUAL

def make_comm_world(process_count):
    table = range(process_count)
    group = Group(table)
    return Communicator(consts.MPI_COMM_WORLD, group)

def make_comm_self(pid):
    group = Group([pid])
    return Communicator(consts.MPI_COMM_SELF, group)

def comm_id_name(comm_id):
    if comm_id == consts.MPI_COMM_WORLD:
        return "MPI_COMM_WORLD"
    if comm_id == consts.MPI_COMM_SELF:
        return "MPI_COMM_SELF"
    return str(comm_id)
