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


class InvalidArgument(ErrorMessage):

    name = "invalidarg"
    short_description = "Invalid argument"

    def __init__(self, function_name,
                       arg_value, arg_position=None,
                       extra_message=""):
        ErrorMessage.__init__(self)
        self.function_name = function_name
        self.arg_value = arg_value
        self.arg_position = arg_position
        self.extra_message = extra_message

    @property
    def description(self):
        return "Function '{0.function_name}' was called with an invalid " \
               "value ({0.arg_value}) in {0.arg_position}. argument. {1}" \
               .format(self, self.extra_message)


class RuntimeErr(ErrorMessage):

    def __init__(self, args):
        pass


class HeapExhausted(RuntimeErr):

    name = "heaperror"
    short_description = "Heap exhausted"
    description = "Process allocated more memory on heap than limit. "\
                  "Use argument --heapsize to bigger value."


class InvalidWrite(RuntimeErr):

    name = "invalidwrite"
    short_description = "Invalid write"

    def __init__(self, args):
        self.addr, self.size = map(int, args)

    @property
    def description(self):
        return "Invalid write of size {0.size} at address " \
               "0x{0.addr:08X}".format(self)


def make_runtime_err(code, args):
    runtime_errors = [ HeapExhausted,
                       InvalidWrite ]
    for e in runtime_errors:
        if e.name == code:
            return e(args)
    e = RuntimeErr()
    e.name = code
    return e
