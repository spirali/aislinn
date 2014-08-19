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

# ---- Basic consts ---------------------------------------
MPI_ANY_SOURCE = 0xFFFF
MPI_ANY_TAG = -0xABF1

MPI_STATUS_IGNORE = 0
MPI_STATUSES_IGNORE = 0

# ---- Data types -----------------------------------------
MPI_PACKED = 0xFF00101
MPI_BYTE = 0xFF00102
MPI_CHAR = 0xFF00103
MPI_UNSIGNED_CHAR = 0xFF00104
MPI_SIGNED_CHAR = 0xFF00105
MPI_WCHAR = 0xFF00106
MPI_SHORT = 0xFF00107
MPI_UNSIGNED_SHORT = 0xFF00108
MPI_INT = 0xFF00109
MPI_UNSIGNED = 0xFF0010A
MPI_LONG = 0xFF0010B
MPI_UNSIGNED_LONG = 0xFF0010C
MPI_LONG_LONG_INT = 0xFF0010D
MPI_UNSIGNED_LONG_LONG = 0xFF0010E
MPI_FLOAT = 0xFF0010F
MPI_DOUBLE = 0xFF00110
MPI_LONG_DOUBLE = 0xFF00111

# ---- Operations -----------------------------------------
MPI_MAX = 0xDD00101
MPI_MIN = 0xDD00102
MPI_SUM = 0xDD00103
MPI_PROD = 0xDD00104
MPI_LAND = 0xDD00105
MPI_BAND = 0xDD00106
MPI_LOR = 0xDD00107
MPI_BOR = 0xDD00109
MPI_LXOR = 0xDD00110
MPI_BXOR = 0xDD00111

