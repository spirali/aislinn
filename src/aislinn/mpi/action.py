#
#    Copyright (C) 2015 Stanislav Bohm
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

import base.utils as utils
import copy

class Action(utils.EqMixin):

    def transfer(self, transfer_context):
        return self


class ActionMatching(utils.EqMixin):

    def __init__(self, matching):
        self.matching = matching

    def apply_action(self, gcontext):
        gcontext.apply_matching(self.matching)

    def transfer(self, transfer_context):
        action = copy.copy(self)
        source_pid, s, target_pid, r = self.matching
        s = transfer_context.translate_table[s]
        r = transfer_context.translate_table[r]
        action.matching = (source_pid, s, target_pid, r)
        return action

    """
    def is_dependent(self, action):
        return (self.matching[2] == action.matching[2]
                and self.matching[3] == action.matching[3])
    """


class ActionWaitAny(Action):

    def __init__(self, pid, index):
        self.pid = pid
        self.index = index

    def apply_action(self, gcontext):
        context = gcontext.prepare_context(self.pid)
        context.continue_waitany(self.index)
        context.state.set_ready()


class ActionWaitSome(Action):

    def __init__(self, pid, indices):
        self.pid = pid
        self.indices = indices

    def apply_action(self, gcontext):
        context = gcontext.prepare_context(self.pid)
        context.continue_waitsome(self.indices)
        context.state.set_ready()


class ActionFlag0(Action):

    def __init__(self, pid):
        self.pid = pid

    def apply_action(self, gcontext):
        context = gcontext.prepare_context(self.pid)
        context.controller.write_int(context.state.flag_ptr, 0)
        context.state.set_ready()


class ActionProbePromise(Action):

    def __init__(self, pid, comm_id, source, tag, rank):
        self.pid = pid
        self.comm_id = comm_id
        self.source = source
        self.tag = tag
        self.rank = rank

    def apply_action(self, gcontext):
        state = gcontext.gstate.states[self.pid]
        state.set_probe_promise(self.comm_id, self.source, self.tag, self.rank)


class ActionTestAll(Action):

    def __init__(self, pid):
        self.pid = pid

    def apply_action(self, gcontext):
        context = gcontext.prepare_context(self.pid)
        context.continue_testall()
        context.state.set_ready()
