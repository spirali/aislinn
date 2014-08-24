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

class Communicator:

    def __init__(self, comm_id, group):
        self.comm_id = comm_id
        self.group = group

    def compute_hash(self, hashthread):
        hashthread.update(str(self.comm_id))
        hashthread.update(str(self.group.table))


class Group:

    def __init__(self, table):
        self.table = table

    @property
    def size(self):
        return len(self.table)

    def is_valid_rank(self, rank):
        return rank >= 0 and rank < len(self.table)

    def rank_to_pid(self, rank):
        return self.table[rank]

    def pid_to_rank(self, pid):
        try:
            return self.table.index(pid)
        except ValueError:
            return None


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

