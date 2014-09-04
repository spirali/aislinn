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


class Message(EqMixin):

    def __init__(self, comm_id, source, target, tag, vg_buffer, size):
        self.comm_id = comm_id
        self.source = source
        self.target = target
        self.tag = tag
        self.vg_buffer = vg_buffer
        self.size = size

    def compute_hash(self, hashthread):
        hashthread.update("M {0.comm_id} {0.source} {0.target} "
                          "{0.tag} {0.size} {0.vg_buffer.hash} ".format(self))

    def __repr__(self):
        return "MESSAGE(source={0.source}, tag={0.tag})".format(self)
