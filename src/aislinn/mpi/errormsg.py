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
import event


class ErrorMessage(object):

    stacktrace = None
    pid = None
    fn_name = None
    explanation = ""
    arg_names = ()
    optional_arg_names = ()
    other_stacktraces = ()

    stdout = None
    stderr = None

    events = None
    node = None

    def __init__(self, context, pid=None, gcontext=None, **kw):
        for name in self.optional_arg_names:
            if name not in kw:
                kw[name] = None
        k = set(kw.keys())
        a = set(self.arg_names)
        if not (a.union(set(self.optional_arg_names)) >= set(k) and a <= k):
            raise Exception(
                "Invalid args for {0}: mandatory args {1}, "
                "optional args {2}, got {3}"
                .format(type(self), self.arg_names,
                        self.optional_arg_names, k))
        self.args = kw
        if context is not None:
            if context.state:
                self.pid = context.state.pid
            context.make_fail_node()
            self.node = context.gcontext.node
            if context.event:
                if context.event.stacktrace:
                    self.stacktrace = context.event.stacktrace
                if isinstance(context.event, event.CallEvent):
                    self.fn_name = context.event.name
            elif context.controller:
                self.stacktrace = context.controller.get_stacktrace()
        elif gcontext is not None:
            self.pid = pid
            self.node = gcontext.node

    @property
    def description(self):
        return self.description_format.format(self, **self.args)


class Deadlock(ErrorMessage):

    key = "mpi/deadlock"
    name = "Deadlock"
    description_format = \
        "Program ends in a deadlock. Proceses {active_pids} are blocked."
    arg_names = ("active_pids",)


class NonzeroExitCode(ErrorMessage):

    key = "base/exitcode"
    name = "Nonzero exitcode"
    description_format = "Process finished with exit code {exitcode}."
    arg_names = ("exitcode",)


class InvalidArg(ErrorMessage):

    message = ""
    arg_names = ("value", "arg_position")
    optional_arg_names = ("index",)

    @property
    def arg_desc(self):
        text = " {0.arg_name} argument for function <em>{0.fn_name}</em>"
        if self.args["index"] is not None:
            text += " ({index}. item of array)"
        return text.format(self, **self.args)

    @property
    def value_text(self):
        value = self.args["value"]
        name = consts.get_const_name(value)
        if name:
            return name + "/" + str(value)
        else:
            return str(value)

    @property
    def arg_name(self):
        if self.args["arg_position"] is not None:
            return "{0}.".format(self.args["arg_position"])
        else:
            return "an"


class InvalidRank(InvalidArg):
    key = "mpi/invalid-arg/rank"
    name = "Invalid rank"
    description_format = \
        "Invalid rank <em>{0.value_text}</em> was used as {0.arg_desc}."


class InvalidRequest(InvalidArg):
    key = "mpi/invalid-arg/request"
    name = "Invalid request"
    description_format = \
        "Invalid request <em>{0.value_text}</em> was used as {0.arg_desc}."


class NotPersistentRequest(InvalidArg):
    key = "mpi/invalid-arg/not-persistent-request"
    name = "Request is not persistent"
    description_format = \
        "Non-persistent request was used as {0.arg_desc}."


class ActivePersistentRequest(InvalidArg):
    key = "mpi/invalid-arg/already-active-persistent-request"
    name = "Starting active persistent request"
    description_format = \
        "Starting already active persistent request."


class InvalidTag(InvalidArg):
    key = "mpi/invalid-arg/tag"
    name = "Invalid tag"
    description_format = \
        "Invalid tag <em>{0.value_text}</em> was used as {0.arg_desc}."


class InvalidCount(InvalidArg):
    key = "mpi/invalid-arg/count"
    name = "Invalid count"
    description_format = \
        "Invalid count <em>{0.value_text}</em> was used as {0.arg_desc}."
    explanation = "Count has to be a non-negative integer."


class InvalidDatatype(InvalidArg):
    name = "Invalid datatype"
    description_format = \
        "Invalid datatype <em>{0.value_text}</em> was used as {0.arg_desc}."
    key = "mpi/invalid-arg/datatype"


class InvalidColor(InvalidArg):
    key = "mpi/invalid-arg/color"
    name = "Invalid color"
    description_format = \
        "Invalid color <em>{0.value_text}</em> was used as {0.arg_desc}."


class InvalidGroup(InvalidArg):
    key = "mpi/invalid-arg/group"
    name = "Invalid group"
    description_format = \
        "Invalid group <em>{0.value_text}</em> was used as {0.arg_desc}."


class InvalidCommunicator(InvalidArg):
    key = "mpi/invalid-arg/communicator"
    name = "Invalid communicator"
    description_format = \
        "An invalid communicator <em>{0.value_text}</em> " \
        "was used as {0.arg_desc}."


class InvalidOperation(InvalidArg):
    key = "mpi/invalid-arg/operation"
    name = "Invalid operation"
    description_format = \
        "Invalid operation <em>{0.value_text}</em> was used as {0.arg_desc}."


class InvalidKeyval(InvalidArg):
    key = "mpi/invalid-arg/keyval"
    name = "Invalid keyval"
    description_format = \
        "Invalid keyval <em>{0.value_text}</em> was used as {0.arg_desc}."


class NonUniqueValues(InvalidArg):
    key = "mpi/invalid-arg/non-unique-values"
    name = "Non-unique values"
    description_format = \
        "Non-unique values {value} were used as {0.arg_desc}."
    message = "Values are non-unique"


class UncommitedDatatype(InvalidArg):
    key = "mpi/invalid-arg/uncommited-datatype"
    name = "Uncommited datatype"
    description_format = \
        "An uncommited datatype was used as {0.arg_desc}."


class InvalidLength(InvalidArg):
    key = "mpi/invalid-arg/length"
    name = "Invalid length"
    description_format = \
        "Value {value} is an invalid length; " \
        "it is {index}. item of an array provided as {0.arg_desc}"


class NoMpiCall(ErrorMessage):
    key = "mpi/no-mpi-call"
    name = "No MPI routine was called"
    description_format = "Program terminated without calling any MPI routine."


class NoMpiInit(ErrorMessage):
    key = "mpi/init-missing"
    name = "MPI_Init was not called"
    description_format = \
        "Program calls an MPI routine without calling MPI_Init."


class InvalidReceiveBuffer(ErrorMessage):
    key = "mpi/invalid-recv-buffer"
    name = "Invalid receive buffer"
    description_format = "Invalid receive buffer. " \
        "Address 0x{address:x} is not accessible."
    arg_names = ("address",)


class InvalidSendBuffer(ErrorMessage):
    key = "mpi/invalid-send-buffer"
    name = "Invalid send buffer"
    description_format = "Invalid send buffer. " \
        "Address 0x{address:x} is not accessible."
    arg_names = ("address",)


class RemovingBuildinDatatype(ErrorMessage):
    key = "mpi/removing-buildin-datatype"
    name = "Removing build-in datatype"
    description_format = "The program attempts to remove " \
                         "build-in datatype <em>{datatype.name}</em>."
    explanation = "Build-in datatypes cannot be removed"
    arg_names = ("datatype",)


class InvalidBufferForProcessorName(ErrorMessage):
    key = "mpi/invalid-processor-name-buffer"
    name = "Invalid buffer for processor name"
    description_format = "Invalid buffer for processor name."


class FreeingPermanentComm(ErrorMessage):
    key = "mpi/freeing-permanent-comm"
    name = "Freeing permanent communicator"
    description_format = \
        "Attemp to free permanenent communicator {0.comm_name}."
    arg_names = ("comm_id",)

    @property
    def comm_name(self):
        return consts.get_const_name(self.args["comm_id"])


class MemoryLeak(ErrorMessage):

    key = "mem/nondeterministic-leak"
    name = "Nondeterministic memory leak"
    arg_names = ("address", "size")
    description_format = \
        "Memory at 0x{address:x} of size {size} was not freed."


class NotFreedRequest(ErrorMessage):

    key = "mpi/pending-request"
    name = "Pending request"
    description_format = "A {request_name} request was not finished."
    arg_names = ("request_name",)


class NotReceivedMessage(ErrorMessage):

    key = "mpi/pending-message"
    name = "Pending message"
    description_format = "A message from rank {source} to rank {target} " \
        "(tag={tag}) was not received. "
    arg_names = ("source", "target", "tag")


class HeapExhausted(ErrorMessage):

    key = "mem/heap-limit-reached"
    name = "Heap limit reached"
    description_format = "Process allocated more memory on heap than limit. "\
                         "Use argument --heapsize to bigger value."


class InvalidRead(ErrorMessage):

    key = "mem/invalid-read"
    name = "Invalid read"
    arg_names = ("address", "size")
    description_format = \
        "Invalid read of size {size} at address 0x{address:08X}"

    def __init__(self, context, **kw):
        ErrorMessage.__init__(self, context, **kw)
        if context.state:
            address = kw["address"]
            stacktrace = context.state.get_locked_memory_stacktrace(address)
            if stacktrace:
                self.other_stacktraces = \
                    (("MPI call that locked the memory", stacktrace),)


class InvalidWrite(ErrorMessage):

    key = "mem/invalid-write"
    name = "Invalid write"
    arg_names = ("address", "size")
    description_format = \
        "Invalid write of size {size} at address 0x{address:08X}"

    def __init__(self, context, **kw):
        ErrorMessage.__init__(self, context, **kw)
        if context.state:
            address = kw["address"]
            stacktrace = context.state.get_locked_memory_stacktrace(address)
            if stacktrace:
                self.other_stacktraces = \
                    (("MPI call that locked the memory", stacktrace),)


class RootMismatch(ErrorMessage):
    key = "mpi/collective-mismatch/root"
    name = "Collective operation: root mismatch"
    description_format = "Root mismatches in the collective operation: " \
                         "{value1} != {value2}"
    arg_names = ("value1", "value2")


class CountMismatch(ErrorMessage):
    key = "mpi/collective-mismatch/count"
    name = "Collective operation: count mismatch"
    description_format = "Count mismatches in the collective operation: " \
                         "{value1} != {value2}"
    arg_names = ("value1", "value2")


class MessageTruncated(ErrorMessage):
    key = "mpi/message-truncated"
    name = "Message truncated"
    description_format = "Message size ({message_size}) is bigger than " \
                         "receive buffer ({buffer_size})."
    arg_names = ("message_size", "buffer_size")


class InvalidInPlace(ErrorMessage):
    key = "mpi/collective-invalid-in-place"
    name = "Invalid use of MPI_IN_PLACE"
    description = "Invalid use of MPI_IN_PLACE"


class CollectiveMixing(ErrorMessage):
    key = "mpi/collective-mixing/type"
    name = "Collective operation mismatch"
    description_format = \
        "Two processes have called different collective operations."


class CollectiveMixingBlockingNonBlocking(ErrorMessage):
    key = "mpi/collective-mixing/blocking-nonblocking"
    name = "Mixing blocking and nonblocking collective operation"
    description_format = \
        "Mixing blocking and nonblocking collective operation"


class DoubleFinalize(ErrorMessage):
    key = "mpi/double-finalize"
    name = "MPI_Finalize called twice"
    description_format = "MPI_FInalize called twice"


class AbortCalled(ErrorMessage):
    key = "mpi/abort"
    name = "MPI_Abort was called"
    description_format = "MPI_Abort called with exitcode={exitcode}"
    arg_names = ("exitcode",)


class AttributeNotFound(ErrorMessage):
    key = "mpi/invalid-arg/attribute"
    name = "Attribute not found"
    description_format = "Attribute was not found in the communicator."


class ExitInCallback(ErrorMessage):
    key = "base/exit-in-callback"
    name = "Program terminated in callback"
    description_format = "Program terminated in a callback."


class CommunicationInCallback(ErrorMessage):
    key = "mpi/communication-in-callback"
    name = "Communication function called in callback"
    description_format = "Communication function was called in a callback."


class GroupMismatch(ErrorMessage):
    key = "mpi/invalid-arg/group-mismatch"
    name = "Group mismatch"
    description_format = \
        "All processes were not called with a same group argument"


#  Debugging messages

class StateCaptured(ErrorMessage):
    key = "internal/state-captured"
    name = "Internal: State captured"
    description_format = "The state '{uid}' was captured " \
                         "because of option --debug-state."
    arg_names = ("uid")
