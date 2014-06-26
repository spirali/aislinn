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


class Arc:

    def __init__(self, node, events):
        self.node = node
        self.events = events

    @property
    def label(self):
        if not self.events:
            return "no-events"
        ranks = list(set(e.rank for e in self.events))
        return ",".join(map(str, ranks))


class Node:

    def __init__(self, uid, hash):
        self.uid = uid
        self.hash = hash
        self.arcs = []
        self.prev = None

    def add_arc(self, arc):
        self.arcs.append(arc)
