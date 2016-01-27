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
import consts

# TODO: vgtool should inform about real sizes of the architecture,
# this constants are just for amd64 on my configuration ...


class Datatype(object):

    def __init__(self):
        self.type_id = None
        self.commited = False

    def get_count(self, size):
        if size % self.size == 0:
            return size / self.size
        else:
            return None

    def is_buildin(self):
        return False


class BuildinType(Datatype):

    def __init__(self, type_id, name, size):
        Datatype.__init__(self)
        self.type_id = type_id
        self.name = name
        self.size = size
        self.commited = True

    def is_buildin(self):
        return True

    def pack(self, controller, pointer, vg_buffer, count, index=0):
        controller.write_into_buffer(vg_buffer.id,
                                     index,
                                     pointer,
                                     self.size * count)

    def pack2(self, controller, pointer, count, callback):
        callback(controller.read_mem(pointer, self.size * count))

    def unpack(self, controller, vg_buffer, count,
               pointer, index=0, check=True):
        controller.write_buffer(
            pointer, vg_buffer.id, index, self.size * count, check)

    def check(self, controller, pointer, count, read=False, write=False):
        if read:
            r = controller.is_readable(pointer, self.size * count)
            if r != "Ok":
                return r
        if write:
            r = controller.is_writable(pointer, self.size * count)
            if r != "Ok":
                return r
        return None

    def lock_memory(self, controller, pointer, count, unlock=False):
        if unlock:
            controller.unlock_memory(pointer, self.size * count)
        else:
            controller.lock_memory(pointer, self.size * count)


class ContiguousType(Datatype):

    def __init__(self, datatype, count):
        Datatype.__init__(self)
        self.datatype = datatype
        self.count = count
        self.size = datatype.size * count

    def pack(self, controller, pointer, vg_buffer, count, index=0):
        self.datatype.pack(
            controller, pointer, vg_buffer, count * self.count, index)

    def pack2(self, controller, pointer, count, callback):
        self.datatype.pack2(
            controller, pointer, count * self.count, callback)

    def unpack(self, controller, vg_buffer, count,
               pointer, index=0, check=True):
        self.datatype.unpack(
            controller, vg_buffer, count * self.count,
            pointer, index, check)

    def check(self, controller, pointer, count, read=False, write=False):
        return self.datatype.check(controller, pointer,
                                   count * self.count, read, write)

    def lock_memory(self, controller, pointer, count, unlock=False):
        self.datatype.lock_memory(
            controller, pointer, count * self.count, unlock)


class VectorType(Datatype):

    def __init__(self, datatype, count, blocksize, stride, is_hvector):
        Datatype.__init__(self)
        self.datatype = datatype
        self.count = count
        self.blocksize = blocksize

        if is_hvector:  # In hvector, stride is already given in bytes
            self.stride = stride
        else:
            self.stride = stride * datatype.size
        self.size = datatype.size * count * blocksize

    def pack(self, controller, pointer, vg_buffer, count, index=0):
        step_index = self.datatype.size * self.blocksize
        for i in xrange(count):
            for j in xrange(self.count):
                self.datatype.pack(
                    controller, pointer, vg_buffer, self.blocksize, index)
                pointer += self.stride
                index += step_index
            pointer -= self.stride
            pointer += step_index

    def pack2(self, controller, pointer, count, callback):
        step_index = self.datatype.size * self.blocksize
        for i in xrange(count):
            for j in xrange(self.count):
                self.datatype.pack2(
                    controller, pointer, self.blocksize, callback)
                pointer += self.stride
            pointer -= self.stride
            pointer += step_index

    def unpack(self, controller, vg_buffer, count,
               pointer, index=0, check=True):
        step_index = self.datatype.size * self.blocksize
        for i in xrange(count):
            for j in xrange(self.count):
                self.datatype.unpack(
                    controller, vg_buffer, self.blocksize,
                    pointer, index, check)
                pointer += self.stride
                index += step_index
            pointer -= self.stride
            pointer += step_index

    def check(self, controller, pointer, count, read=False, write=False):
        for i in xrange(count):
            for j in xrange(self.count):
                r = self.datatype.check(
                    controller, pointer, self.blocksize, read, write)
                if r is not None:
                    return r
                pointer += self.stride
            pointer -= self.stride

    def lock_memory(self, controller, pointer, count, unlock=False):
        for i in xrange(count):
            for j in xrange(self.count):
                self.datatype.lock_memory(
                    controller, pointer, self.blocksize, unlock)
                pointer += self.stride
            pointer -= self.stride


class IndexedType(Datatype):

    def __init__(self, datatype, count, sizes, displs, is_hindexed):
        assert count == len(sizes) == len(displs)
        Datatype.__init__(self)
        self.datatype = datatype
        self.count = count
        self.sizes = sizes
        if is_hindexed:  # In hindexed, displs is already given in bytes
            self.displs = displs
        else:
            self.displs = [displ * datatype.size for displ in displs]
        self.size = datatype.size * sum(sizes)
        self.unpack_size = max(displ + self.datatype.size * size
                               for size, displ in zip(self.sizes, self.displs))

    def pack(self, controller, pointer, vg_buffer, count, index=0):
        for i in xrange(count):
            for j in xrange(self.count):
                self.datatype.pack(
                    controller,
                    pointer + self.displs[j],
                    vg_buffer,
                    self.sizes[j],
                    index)
                index += self.sizes[j] * self.datatype.size
            pointer += self.unpack_size

    def pack2(self, controller, pointer, count, callback):
        for i in xrange(count):
            for j in xrange(self.count):
                self.datatype.pack2(
                    controller,
                    pointer + self.displs[j],
                    self.sizes[j],
                    callback)
            pointer += self.unpack_size

    def unpack(self, controller, vg_buffer, count,
               pointer, index=0, check=True):
        for i in xrange(count):
            for j in xrange(self.count):
                self.datatype.unpack(
                    controller,
                    vg_buffer,
                    self.sizes[j],
                    pointer + self.displs[j],
                    index,
                    check)
                index += self.sizes[j] * self.datatype.size
            pointer += self.unpack_size

    def check(self, controller, pointer, count, read=False, write=False):
        for i in xrange(count):
            for j in xrange(self.count):
                r = self.datatype.check(
                    controller,
                    pointer + self.displs[j],
                    self.sizes[j],
                    read, write)
                if r is not None:
                    return r
            pointer += self.unpack_size

    def lock_memory(self, controller, pointer, count, unlock=False):
        for i in xrange(count):
            for j in xrange(self.count):
                self.datatype.lock_memory(
                    controller,
                    pointer + self.displs[j],
                    self.sizes[j],
                    unlock)
            pointer += self.unpack_size


class StructType(Datatype):

    def __init__(self, datatypes, counts, displs):
        assert len(datatypes) == len(counts) == len(displs)
        Datatype.__init__(self)
        self.datatypes = datatypes
        self.counts = counts
        self.displs = displs
        self.size = sum(datatype.size * count
                        for datatype, count in zip(datatypes, counts))
        self.unpack_size = max(displ + datatype.size * count
                               for datatype, count, displ
                               in zip(datatypes, counts, displs))

    def pack(self, controller, pointer, vg_buffer, count, index=0):
        for i in xrange(count):
            for datatype, c, displ in \
                    zip(self.datatypes, self.counts, self.displs):
                datatype.pack(controller,
                              pointer + displ,
                              vg_buffer,
                              c,
                              index)
                index += c * datatype.size
            pointer += self.unpack_size

    def pack2(self, controller, pointer, count, callback):
        for i in xrange(count):
            for datatype, c, displ in \
                    zip(self.datatypes, self.counts, self.displs):
                datatype.pack2(controller,
                               pointer + displ,
                               c,
                               callback)
            pointer += self.unpack_size

    def unpack(self, controller, vg_buffer, count,
               pointer, index=0, check=True):
        for i in xrange(count):
            for datatype, c, displ in \
                    zip(self.datatypes, self.counts, self.displs):
                datatype.unpack(controller,
                                vg_buffer,
                                count,
                                pointer + displ,
                                index,
                                check)
                index += c * datatype.size
            pointer += self.unpack_size

    def check(self, controller, pointer, count, read=False, write=False):
        for i in xrange(count):
            for datatype, c, displ in \
                    zip(self.datatypes, self.counts, self.displs):
                r = datatype.check(controller,
                                   pointer + displ,
                                   c,
                                   read,
                                   write)
                if r is not None:
                    return r
            pointer += self.unpack_size

    def lock_memory(self, controller, pointer, count, unlock=False):
        for i in xrange(count):
            for datatype, c, displ in \
                    zip(self.datatypes, self.counts, self.displs):
                r = datatype.lock_memory(controller,
                                         pointer + displ,
                                         c,
                                         unlock)
                if r is not None:
                    return r
            pointer += self.unpack_size


buildin_types = dict((t.type_id, t) for t in [
    BuildinType(consts.MPI_PACKED, "MPI_PACKED", 1),
    BuildinType(consts.MPI_BYTE, "MPI_BYTE", 1),
    BuildinType(consts.MPI_CHAR, "MPI_CHAR", 1),
    BuildinType(consts.MPI_UNSIGNED_CHAR, "MPI_UNSIGNED_CHAR", 1),
    BuildinType(consts.MPI_SIGNED_CHAR, "MPI_SIGNED_CHAR", 1),
    BuildinType(consts.MPI_WCHAR, "MPI_WCHAR", 2),
    BuildinType(consts.MPI_SHORT, "MPI_SHORT", 2),
    BuildinType(consts.MPI_UNSIGNED_SHORT, "MPI_UNSIGNED_SHORT", 2),
    BuildinType(consts.MPI_INT, "MPI_INT", 4),
    BuildinType(consts.MPI_UNSIGNED, "MPI_UNSIGNED", 4),
    BuildinType(consts.MPI_LONG, "MPI_LONG", 8),
    BuildinType(consts.MPI_UNSIGNED_LONG, "MPI_UNSIGNED_LONG", 8),
    BuildinType(consts.MPI_LONG_LONG_INT, "MPI_LONG_LONG_INT", 8),
    BuildinType(consts.MPI_UNSIGNED_LONG_LONG, "MPI_UNSIGNED_LONG_LONG", 8),
    BuildinType(consts.MPI_FLOAT, "MPI_FLOAT", 4),
    BuildinType(consts.MPI_DOUBLE, "MPI_DOUBLE", 8),
    BuildinType(consts.MPI_LONG_DOUBLE, "MPI_LONG_DOUBLE", 16),
    BuildinType(consts.MPI_FLOAT_INT, "MPI_FLOAT_INT", 8),
    BuildinType(consts.MPI_DOUBLE_INT, "MPI_DOUBLE_INT", 16),
    BuildinType(consts.MPI_LONG_INT, "MPI_LONG_INT", None),
    BuildinType(consts.MPI_2INT, "MPI_2INT", 8),
    BuildinType(consts.MPI_SHORT_INT, "MPI_SHORT_INT", None),
    BuildinType(consts.MPI_LONG_DOUBLE_INT, "MPI_LONG_DOUBLE_INT", None),
])
