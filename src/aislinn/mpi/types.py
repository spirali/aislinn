
import consts

# TODO: vgtool should inform about real sizes of the architecture,
# this constants are just for amd64 on my configuration ...


class Datatype(object):

    def __init__(self):
        self.type_id = None
        self.commited = False


class BuildinType(Datatype):

    def __init__(self, type_id, name, size):
        Datatype.__init__(self)
        self.type_id = type_id
        self.name = name
        self.size = size
        self.commited = True

    def pack(self, controller, pointer, vg_buffer, count, index=0):
        controller.write_into_buffer(vg_buffer.id,
                                     index,
                                     pointer,
                                     self.size * count)


    def unpack(self, controller, vg_buffer, count, pointer, index=0):
        controller.write_buffer(pointer, vg_buffer.id, index, self.size * count)


class ContiguousType(Datatype):

    def __init__(self, datatype, count):
        self.datatype = datatype
        self.count = count
        self.size = datatype.size * count

    def pack(self, controller, pointer, vg_buffer, count, index=0):
        self.datatype.pack(
                controller, pointer, vg_buffer, count * self.count, index)

    def unpack(self, controller, vg_buffer, count, pointer, index=0):
        self.datatype.unpack(
                controller, vg_buffer, count * self.count, pointer, index)


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

op_names = {
    consts.MPI_MAX : "MPI_MAX",
    consts.MPI_MIN : "MPI_MIN",
    consts.MPI_SUM : "MPI_SUM",
    consts.MPI_PROD : "MPI_PROD",
    consts.MPI_LAND : "MPI_LAND",
    consts.MPI_BAND : "MPI_BAND",
    consts.MPI_LOR : "MPI_LOR",
    consts.MPI_BOR : "MPI_BOR",
    consts.MPI_LXOR : "MPI_LXOR",
    consts.MPI_BXOR : "MPI_BXOR",
    consts.MPI_MINLOC : "MPI_MINLOC",
    consts.MPI_MAXLOC : "MPI_MAXLOC",
}

vgtool_name_of_types = {
    consts.MPI_INT: "int",
    consts.MPI_DOUBLE: "double",
    consts.MPI_DOUBLE_INT: "double_int",
    consts.MPI_2INT : "int_int",
}

vgtool_name_of_ops = {
    consts.MPI_SUM: "+",
    consts.MPI_PROD: "*",
    consts.MPI_MINLOC: "minloc",
    consts.MPI_MAXLOC: "maxloc",
}

def is_valid_op(op):
    return op >= consts.MPI_MIN and op <= consts.MPI_MAXLOC

def get_op_name(op):
    return op_names.get(op)

def translate_reduction_op(datatype, op):
    # TODO: This is just an experimental implementation
    if datatype.type_id in vgtool_name_of_types and op in vgtool_name_of_ops:
        return vgtool_name_of_types[datatype.type_id], vgtool_name_of_ops[op]
    raise Exception("Unsuported operation for datatype {0}" \
            .format(datatype.name))
