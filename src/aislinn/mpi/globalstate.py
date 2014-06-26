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


import hashlib
from base.utils import EqMixin


class GlobalState(EqMixin):

    def __init__(self, states, send_protocol_thresholds):
        self.states = tuple(states)
        self.send_protocol_thresholds = send_protocol_thresholds

    def copy(self):
        states = [ state.copy() for state in self.states ]
        return GlobalState(states, self.send_protocol_thresholds)

    def dispose(self):
        for state in self.states:
            state.dispose()

    def get_state(self, rank):
        return self.states[rank]

    def compute_hash(self):
        for state in self.states:
            # If state is not hashed we cannot have a global hash
            if not state.is_hashable():
                return None
        hashthread = hashlib.md5()
        if self.send_protocol_thresholds:
            hashthread.update(str(self.send_protocol_thresholds))
        for state in self.states:
            state.compute_hash(hashthread)
        return hashthread.hexdigest()

    @property
    def states_count(self):
        return len(self.states)
