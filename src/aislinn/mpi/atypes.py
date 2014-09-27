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

import check
from base.utils import convert_type

class Arg:

    c_type = "invalid"

    @classmethod
    def convert(cls, value, arg_position, state):
        return value

    @classmethod
    def make_conversion(cls, value, arg_position, state):
        return cls.convert(convert_type(value, cls.c_type), arg_position, state)


class Pointer(Arg):
    c_type = "ptr"


class Int(Arg):
    c_type = "int"


class Comm(Int):

    @classmethod
    def convert(cls, value, arg_position, state):
        return check.check_comm(state, value, arg_position)


class Group(Int):

    @classmethod
    def convert(cls, value, arg_position, state):
        return check.check_and_get_group(state, value, arg_position)


class Op(Int):

    @classmethod
    def convert(cls, value, arg_position, state):
        return check.check_op(value, arg_position)


class Count(Int):

    @classmethod
    def convert(cls, value, arg_position, state):
        return check.check_count(value, arg_position)


class Datatype(Int):

    @classmethod
    def convert(cls, value, arg_position, state):
        return check.check_datatype(state, value, arg_position)


class DatatypeU(Int): # Uncommited

    @classmethod
    def convert(cls, value, arg_position, state):
        return check.check_datatype(state, value, arg_position, True)

class Rank(Int):
    pass

class Tag(Int):
    @classmethod
    def convert(cls, value, arg_position, state):
        return check.check_tag(value, arg_position, False)


class TagAT(Int): # Allow MPI_ANY_TAG
    @classmethod
    def convert(cls, value, arg_position, state):
        return check.check_tag(value, arg_position, True)
