#
#    Copyright (C) 2014, 2015 Stanislav Bohm
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


class Event:

    stacktrace = None
    new_request = None
    cc = None # Collective communication info (comm_id, cc_id)
    ndsync = False


class CallEvent(Event):

    def __init__(self, name, pid, args=None):
        self.name = name
        self.args = args
        self.pid = pid

    def __repr__(self):
        return "<Event {1} {0.name} pid={0.pid} {0.args}>".format(self, id(self))


class ExitEvent(Event):

    name = "Exit"

    def __init__(self, pid, exitcode):
        self.pid = pid
        self.exitcode = exitcode

    def __repr__(self):
        return "<Event Exit pid={0.pid} exitcode={0.exitcode}>".format(self)


class MatchEvent(Event):

    name = "Match"

    def __init__(self, source_id, target_id):
        self.source_id = source_id
        self.target_id = target_id

    def __repr__(self):
        return "<Event Match source_id={0.source_id} " \
               "target_id={0.target_id}>".format(self)


class Continue(Event):

    name = "Continue"

    def __init__(self, pid, request_ids):
        self.pid = pid
        self.request_ids = tuple(request_ids)

    def __repr__(self):
        return "<Continue pid={0.pid} rids={0.request_ids}>".format(self)
