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


class Tag:

    def __init__(self, name, *args, **kw):
        self.name = name
        self.attributes = []
        self.childs = list(args)
        for k in kw:
            self.attributes.append((k, kw[k]))

    def set(self, name, value):
        self.attributes.append((name, value))

    def write(self, f):
        f.write("<{0}".format(self.name))
        for name, value in self.attributes:
            f.write(" {0}='{1}'".format(name, value))
        if self.childs or self.text:
            f.write(">")
            if self.childs:
                f.write("\n")
            for tag in self.childs:
                if isinstance(tag, Tag):
                    tag.write(f)
                else:
                    f.write(str(tag))
            f.write("</{0}>\n".format(self.name))
        else:
            f.write(" />\n")

    def add_child(self, child):
        self.childs.append(child)

    def text(self, text):
        self.add_child(str(text))

    def child(self, *args, **kw):
        tag = Tag(*args, **kw)
        self.add_child(tag)
        return tag
