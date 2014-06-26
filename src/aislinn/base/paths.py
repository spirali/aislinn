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


import os


AISLINN_ROOT = os.path.dirname(
                os.path.dirname(
                   os.path.dirname(
                     os.path.dirname(os.path.abspath(__file__)))))

VALGRIND = os.path.join(AISLINN_ROOT, "valgrind")
VALGRIND_BIN = os.path.join(VALGRIND, "vg-in-place")
