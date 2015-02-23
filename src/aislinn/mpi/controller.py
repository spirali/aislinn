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


import base.controller

class Controller(base.controller.ControllerWithResources):

    STATUS_SIZE = 4 * base.controller.Controller.INT_SIZE
    REQUEST_SIZE = base.controller.Controller.INT_SIZE

    context = None

    def write_status(self, status_ptr, source, tag, size):
        self.write_ints(status_ptr, [ source, tag, size ])

    def on_unexpected_output(self, line):
        self.context.on_unexpected_output(line)

    def make_buffer_and_pack(self, datatype, count, addr):
        vg_buffer = self.make_buffer(datatype.size * count)
        datatype.pack(self, addr, vg_buffer, count)
        vg_buffer.hash = self.hash_buffer(vg_buffer.id)
        return vg_buffer
