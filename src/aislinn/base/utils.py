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


import re
import ctypes # Used for int type conversions


class EqMixin(object):

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)


integer_parser = re.compile("^\d+$")
def is_integer(value):
    return bool(integer_parser.match(value))

def sizestr_to_int(s):
    if s.endswith("K"):
        m = 1024
    elif s.endswith("M"):
        m = 1024 * 1024
    elif s.endswith("G"):
        m = 1024 * 1024 * 1024
    elif s.endswith("T"):
        m = 1024 * 1024 * 1024 * 1024
    else:
        m = 1

    if m != 1:
        s = s[:-1]

    if not is_integer(s):
        return None
    return int(s) * m

def convert_type(value, target_type):
    if target_type == "ptr":
        return int(value)
    if target_type == "int":
        return ctypes.c_int(int(value)).value

def convert_types(values, target_types):
    assert len(values) == len(target_types)
    return [ convert_type(v, t) for v, t in zip(values, target_types) ]
