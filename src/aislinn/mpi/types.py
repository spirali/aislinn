
import consts

# TODO: vgtool should inform about real sizes of the architecture,
# this constants are just for amd64

type_sizes = {
    consts.MPI_PACKED : 1,
    consts.MPI_BYTE : 1,
    consts.MPI_CHAR : 1,
    consts.MPI_UNSIGNED_CHAR : 1,
    consts.MPI_SIGNED_CHAR : 1,
    consts.MPI_WCHAR : 2,
    consts.MPI_SHORT : 2,
    consts.MPI_UNSIGNED_SHORT : 2,
    consts.MPI_INT : 4,
    consts.MPI_UNSIGNED : 4,
    consts.MPI_LONG : 8,
    consts.MPI_UNSIGNED_LONG : 8,
    consts.MPI_LONG_LONG_INT : 8,
    consts.MPI_UNSIGNED_LONG_LONG : 8,
    consts.MPI_FLOAT : 4,
    consts.MPI_DOUBLE : 8,
    consts.MPI_LONG_DOUBLE : 16,
    consts.MPI_FLOAT_INT : 8,
    consts.MPI_DOUBLE_INT : 16,
    consts.MPI_LONG_INT : None,
    consts.MPI_2INT : 8,
    consts.MPI_SHORT_INT : None,
    consts.MPI_LONG_DOUBLE_INT : None,
}

type_names = {
    consts.MPI_PACKED : "MPI_PACKED",
    consts.MPI_BYTE : "MPI_BYTE",
    consts.MPI_CHAR : "MPI_CHAR",
    consts.MPI_UNSIGNED_CHAR : "MPI_UNSIGNED_CHAR",
    consts.MPI_SIGNED_CHAR : "MPI_SIGNED_CHAR",
    consts.MPI_WCHAR : "MPI_WCHAR",
    consts.MPI_SHORT : "MPI_SHORT",
    consts.MPI_UNSIGNED_SHORT : "MPI_UNSIGNED_SHORT",
    consts.MPI_INT : "MPI_INT",
    consts.MPI_UNSIGNED : "MPI_UNSIGNED",
    consts.MPI_LONG : "MPI_LONG",
    consts.MPI_UNSIGNED_LONG : "MPI_UNSIGNED_LONG",
    consts.MPI_LONG_LONG_INT : "MPI_LONG_LONG_INT",
    consts.MPI_UNSIGNED_LONG_LONG : "MPI_UNSIGNED_LONG_LONG",
    consts.MPI_FLOAT : "MPI_FLOAT",
    consts.MPI_DOUBLE : "MPI_DOUBLE",
    consts.MPI_LONG_DOUBLE : "MPI_LONG_DOUBLE",
    consts.MPI_FLOAT_INT : "MPI_FLOAT_INT",
    consts.MPI_DOUBLE_INT : "MPI_DOUBLE_INT",
    consts.MPI_LONG_INT : "MPI_LONG_INT",
    consts.MPI_2INT : "MPI_2INT",
    consts.MPI_SHORT_INT : "MPI_SHORT_INT",
    consts.MPI_LONG_DOUBLE_INT : "MPI_LONG_DOUBLE_INT",
}

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

def get_datatype_size(datatype, count=1):
    size = type_sizes.get(datatype)
    if size is not None:
        return size * count
    else:
        return None

def get_datatype_name(datatype):
    name = type_names.get(datatype)
    if name is not None:
        return name
    else:
        return "Unknown type (value={0})".format(datatype)

def is_valid_op(op):
    return op >= consts.MPI_MIN and op <= consts.MPI_MAXLOC

def get_op_name(op):
    return op_names.get(op)

def translate_reduction_op(datatype, op):
    # TODO: This is just an experimental implementation
    if datatype in vgtool_name_of_types and op in vgtool_name_of_ops:
        return vgtool_name_of_types[datatype], vgtool_name_of_ops[op]
    raise Exception("Unsuported operation for datatype {0}" \
            .format(get_datatype_name(datatype)))
