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

class ErrorMessage:

    description = ""
    name = "unknown"

    stacktrace = None

    def __init__(self):
        self.node = None
        self.last_arc = None
        self.rank = None
        self.events = None

    def get_entries(self):
        e = EntryList()
        if self.rank is not None:
            e.add("rank", self.rank)
        description = self.description
        if description:
            e.add("description", self.description)
        return e

    @property
    def short_description(self):
        return self.name.capitalize()


class NonzeroExitCode(ErrorMessage):

    name = "exitcode"
    short_description = "Nonzero exit code"

    def __init__(self, exitcode):
        ErrorMessage.__init__(self)
        self.exitcode = exitcode

    @property
    def description(self):
        return "Rank {0.rank} finished with exit code {0.exitcode}" \
                    .format(self)

    def get_entries(self):
        e = ErrorMessage.get_entries(self)
        e.add("exitcode", self.exitcode)
        return e


class Deadlock(ErrorMessage):

    name = "deadlock"
    short_description = "Deadlock"


class RuntimeErr(ErrorMessage):
    pass

def make_runtime_err(code):
    e = RuntimeErr()
    e.name = code
    if code == "heaperror":
        e.short_description = "Heap exhausted"
        e.description = "Process allocated more memory on heap than limit. "\
                        "Use argument --heapsize to bigger value."
    return e
