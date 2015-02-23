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


class Resource:

    def __init__(self, manager, id):
        self.ref_count = 1
        self.manager = manager
        self.id = id

    def inc_ref(self):
        self.ref_count += 1
        assert self.ref_count > 1

    def inc_ref_revive(self):
        self.ref_count += 1
        if self.ref_count == 1:
            self.manager.revive(self)

    def dec_ref(self):
        self.ref_count -= 1
        if self.ref_count < 1:
            #import traceback
            #traceback.print_stack()
            assert self.ref_count == 0
            self.manager.add_not_used_resource(self)

    def __repr__(self):
        return "<{0} {1:x} {2} ref={3}>".format(
                self.__class__, id(self), self.id, self.ref_count)


class ResourceManager:

    def __init__(self, resource_class=Resource):
        self.not_used_resources = None
        self.resource_class = resource_class
        self.resource_count = 0

    def new(self, id):
        self.resource_count += 1
        return self.resource_class(self, id)

    def revive(self, resource):
        assert resource.ref_count == 1
        self.resource_count += 1
        self.not_used_resources.remove(resource)

    def pickup_resources_to_clean(self):
        r = self.not_used_resources
        self.not_used_resources = None
        return r

    def add_not_used_resource(self, resource):
        self.resource_count -= 1
        assert self.resource_count >= 0

        if self.not_used_resources is None:
            self.not_used_resources = [ resource ]
        else:
            self.not_used_resources.append(resource)
