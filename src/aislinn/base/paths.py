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


import os

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AISLINN_ROOT = os.path.dirname(os.path.dirname(SRC_DIR))

AISLINN_TEMPLATE = os.path.join(SRC_DIR, "template")

VALGRIND_LOCAL = os.path.join(AISLINN_ROOT, "valgrind")
VALGRIND_LOCAL_BIN = os.path.join(VALGRIND_LOCAL, "vg-in-place")
VALGRIND_INSTALL_BIN = os.path.join(os.path.dirname(AISLINN_ROOT), "bin", "valgrind")

VALGRIND_BIN = None # Need to be configured
