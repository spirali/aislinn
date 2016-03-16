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


class ArcData:

    def __init__(self, name, pid, value):
        self.name = name
        self.pid = pid
        self.value = value


class Arc:

    worker = None
    time = None

    def __init__(self, node, action, events=(), data=()):
        self.node = node
        self.action = action
        self.events = events
        self.data = data  # list of ArcData

    @property
    def action_index(self):
        if self.action:
            return self.action.action_index
        else:
            return -1

    @property
    def label(self):
        return "{}/{}/{}".format(
            self.action.action_index if self.action else "",
            self.action.name if self.action else "no-act",
            self.worker)

        if not self.events and not self.data:
            return "no-events"
        pids = list(set(e.pid for e in self.events if hasattr(e, "pid")))
        return "{}/{}".format(pids, self.worker)

        l = ",".join(map(str, pids))
        if self.data:
            l += "+d"
        return l

    def get_pids(self):
        return list(set(e.pid for e in self.events if hasattr(e, "pid")))

    def get_data(self, name, pid):
        if self.data:
            for d in self.data:
                if d.name == name and d.pid == pid:
                    return d


class Stream:

    def __init__(self, name):
        self.name = name

    def compact_data(self, data):
        return "".join(data)


STREAM_STDOUT = Stream("<stdout>")
STREAM_STDERR = Stream("<stderr>")


class Counter:

    def __init__(self):
        pass

    def compact_data(self, data):
        return sum(data)


COUNTER_INSTRUCTIONS = Counter()
COUNTER_ALLOCATIONS = Counter()
COUNTER_SIZE_ALLOCATIONS = Counter()
COUNTER_MPICALLS = Counter()
