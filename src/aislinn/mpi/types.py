
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
    consts.MPI_LONG_DOUBLE : 16
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
    consts.MPI_LONG_DOUBLE : "MPI_LONG_DOUBLE"
}

def get_datatype_size(datatype):
    return type_sizes.get(datatype)

def get_datatype_name(datatype):
    name = type_names.get(datatype)
    if name is not None:
        return name
    else:
        return "Unknown type (value={0})".format(datatype)
