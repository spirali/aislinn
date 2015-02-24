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


STREAM_STDOUT = "<stdout>"
STREAM_STDERR = "<stderr>"


class StreamChunk:

    def __init__(self, stream_name, pid, data):
        self.stream_name = stream_name
        self.pid = pid
        self.data = data

    def add_event(self, event):
        self.events.append(event)

    def add_stream_chunk(self, stream_name, pid, data):
        self.stream_chunks.append(((stream_name, pid), data))
