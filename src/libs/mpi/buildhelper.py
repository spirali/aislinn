import sys
import re

# This program generates mpi.c from mpi.h

ignored_functions = set([ "MPI_Init" ])

def get_functions(header):
    results = []
    fstrings = re.findall("^int MPI_[A-Z][a-z_]*\([^\)]*\);",
                          header, re.MULTILINE)
    rexp = re.compile("int (?P<name>MPI_[A-Z][a-z_]*)\((?P<args>[^\)]*)\)")
    for fstring in fstrings:
        match = rexp.match(fstring)
        if match is None:
            continue
        name = match.group("name")
        args = []
        if match.group("args").strip() != "":
            for a in match.group("args").split(","):
                t, n = a.strip().rsplit(" ", 1)
                t = t.strip()
                n = n.strip()
                while n.startswith("*"):
                    n = n[1:]
                    if not t.endswith("*"):
                        t += " "
                    t += "*"
                if n.endswith("[]"):
                    n = n[:-2]
                    tsuffix = "[]"
                else:
                    tsuffix = ""
                args.append((n.strip(), t.strip(), tsuffix))
        if name not in ignored_functions:
            results.append((name, args))
    return results

def compose_c_source(functions):
    lines = []
    for name, args in functions:
        astring = ", ".join("{0} {1}{2}".format(n, t, ts)
                            for t, n, ts in args)
        lines.append("int {0}({1})\n{{".format(name, astring))
        lines.append("\tAislinnArgType args[{0}] = {{\n{1}\n\t}};".format(
            len(args),
            ",\n".join("\t\t (AislinnArgType) {0}".format(n)
                       for n, t, ts in args)
            ))
        lines.append("\taislinn_call(\"{0}\", args, {1});".format(
            name, len(args)));
        lines.append("\treturn MPI_SUCCESS;\n}\n")
    return "\n".join(lines)

def main():
    if len(sys.argv) != 3:
        print "usage: python buildhelper.py <path/mpi.h> <path/mpi.c>"
        sys.exit(1)
    script, mpi_h, mpi_c = sys.argv

    with open(mpi_h, "r") as f:
        functions = get_functions(f.read())

    sources = compose_c_source(functions)

    with open(mpi_c, "w") as f:
        f.write("/****************************************\n")
        f.write("| This is automatically generated file\n")
        f.write("| Do not edit it directly!\n")
        f.write("\***************************************/\n\n")
        f.write("#include<mpi.h>\n\n")
        f.write(sources)

main()
