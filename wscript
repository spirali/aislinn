APPNAME = "Aislinn"
VERSION = "0.0.1"

def options(ctx):
    ctx.load("compiler_cc python")


def configure(ctx):
    ctx.load("compiler_cc python")
    if not ctx.env.CXXFLAGS:
        ctx.env.append_value("CFLAGS", "-O2")
        ctx.env.append_value("CFLAGS", "-g")

    ctx.env.append_value("CFLAGS", "-Wall")

def build(ctx):
    ctx.recurse("src/libs/aislinn")
    ctx.recurse("src/libs/mpi")
