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


class Event:

    stacktrace = None


class CallEvent(Event):

    def __init__(self, name, pid, args=None):
        self.name = name
        self.args = args
        self.pid = pid


class ExitEvent(Event):

    name = "Exit"

    def __init__(self, pid, exitcode):
        self.pid = pid
        self.exitcode = exitcode


class MatchEvent(Event):

    name = "Match"

    def __init__(self, source_pid, target_pid):
        self.source_pid = source_pid
        self.target_pid = target_pid
