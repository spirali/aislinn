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


from base.report import EntryList


class Event:

    stacktrace = None

    def __init__(self, name, pid):
        self.name = name
        self.pid = pid

    def get_entries(self):
        return EntryList()


class CommEvent(Event):

    def __init__(self, name, pid, target, tag, request_id=None):
        Event.__init__(self, name, pid)
        self.target = target
        self.tag = tag
        self.request_id = request_id

class CollectiveEvent(Event):

    def __init__(self, name, pid):
        Event.__init__(self, name, pid)

class WaitEvent(Event):

    def __init__(self, name, pid, request_ids):
        Event.__init__(self, name, pid)
        self.request_ids = request_ids


class ExitEvent(Event):

    def __init__(self, name, pid, exitcode):
        Event.__init__(self, name, pid)
        self.exitcode = exitcode
