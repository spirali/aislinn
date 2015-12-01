APPNAME = "Aislinn"
VERSION = "0.0.1"

from waflib import Utils

BIN_FILES = [
    "bin/aislinn",
    "bin/aislinn-cc",
    "bin/aislinn-c++",
    "bin/mpicc",
    "bin/mpicxx"
]

def options(ctx):
    ctx.load("compiler_cc python")


def configure(ctx):
    ctx.load("compiler_cc python")
    if not ctx.env.CFLAGS:
        ctx.env.append_value("CFLAGS", "-O2")
        ctx.env.append_value("CFLAGS", "-g")

    ctx.env.append_value("CFLAGS", "-Wall")

def build(ctx):
    ctx.recurse("src/libs/aislinn")
    ctx.recurse("src/libs/mpi")
    ctx.recurse("src/aislinn")

    ctx.install_files("${PREFIX}/bin", BIN_FILES, chmod=Utils.O755)
