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


VERSION_STRING = "0.2.0"


from mpi.generator import Generator
from base.stream import STREAM_STDOUT, STREAM_STDERR
import base.utils as utils
import argparse
import os
import sys
import logging
import platform

def parse_threshold(value):
    if ":" not in value:
        size1 = utils.sizestr_to_int(value)
        size2 = size1
    else:
        values = value.split(":", 1)
        size1 = utils.sizestr_to_int(values[0])
        size2 = utils.sizestr_to_int(values[1])
    if size1 is None or size2 is None:
        return None
    return (size1, size2)


def parse_args():
    parser = argparse.ArgumentParser(description=
            "Aislinn -- Statespace analytical tool for MPI applications")
    parser.add_argument("program",
                        metavar="PROGRAM",
                        type=str,
                        help="Path to your program")
    parser.add_argument("args",
                        type=str,
                        nargs=argparse.REMAINDER,
                        help="Arguments for your program")
    parser.add_argument("-p",
                        metavar="N",
                        type=int,
                        default=1,
                        help="Number of processes")
    parser.add_argument("--verbose",
                        metavar="N",
                        type=int,
                        default=1,
                        help="Verbosity level (default: 1)")
    parser.add_argument("--vgv",
                        metavar="N",
                        type=int,
                        default=0,
                        help="Verbosity of valgrind tool")
    parser.add_argument("--heap-size",
                        metavar="SIZE",
                        type=str,
                        help="Maximal size of heap")
    parser.add_argument("--redzone-size",
                        metavar="SIZE",
                        type=int,
                        help="Allocation red zones")
    parser.add_argument("-S", "--send-protocol",
                        metavar="VALUE",
                        type=str,
                        help="Standard send protocol.",
                        default="eager")

    parser.add_argument("--report-type",
                        metavar="TYPE",
                        choices=["html", "xml", "none", "html+xml"],
                        help="Output type: xml, html, none",
                        default="html")

    parser.add_argument("--max-states",
                       metavar="N",
                       type=int,
                       default=9999999)

    parser.add_argument('--stdout',
                        metavar="MODE",
                        choices=["capture", "capture", "print", "drop"],
                        default="capture",
                        help="")

    parser.add_argument('--stdout-write',
                        metavar="N",
                        type=str,
                        default="0",
                        help="")

    parser.add_argument('--stderr',
                        metavar="MODE",
                        choices=["capture", "capture",
                                 "print", "drop", "stdout"],
                        default="capture",
                        help="")

    parser.add_argument('--stderr-write',
                        metavar="N",
                        type=str,
                        default="0",
                        help="0")

    parser.add_argument("--search",
                        metavar="SEARCH",
                        type=str,
                        default="bfs",
                        help="Statespace search strategy (bfs or dfs)")

    parser.add_argument("--stats",
                       metavar="TICKS",
                       type=int,
                       default=None)

    parser.add_argument("--write-dot",
                       action="store_true")

    # Internal debug options
    parser.add_argument("--debug-state",
                       metavar="NAME",
                       type=str,
                       default=None)
    parser.add_argument("--debug-compare-states",
                       metavar="STATE~STATE",
                       type=str,
                       default=None)
    parser.add_argument("--debug-statespace",
                       action="store_true")
    parser.add_argument("--debug-seq",
                       action="store_true")
    parser.add_argument("--debug-by-valgrind-tool",
                        metavar="TOOL",
                        type=str,
                        default=None)
    parser.add_argument("--debug-profile",
                       action="store_true")
    args = parser.parse_args()

    if args.verbose == 0:
        level = logging.ERROR
    elif args.verbose == 1:
        level = logging.INFO
    elif args.verbose == 2:
        level = logging.DEBUG
    else:
        print "Invalid verbose level (parameter --verbose)"
        sys.exit(1)

    if args.stdout_write != "all":
        if utils.is_integer(args.stdout_write):
            args.stdout_write = int(args.stdout_write)
        else:
            sys.stderr.write("Invalid argument for --stdout-write\n")
            sys.exit(1)

    if args.stderr_write != "all":
        if utils.is_integer(args.stderr_write):
            args.stderr_write = int(args.stderr_write)
        else:
            sys.stderr.write("Invalid argument for --stderr-write\n")
            sys.exit(1)

    logging.basicConfig(format="==AN== %(levelname)s: %(message)s",
                        level=level)
    logging.info("Aislinn v%s", VERSION_STRING)

    if args.p <= 0:
        logging.error("Invalid number of processes (parameter -p)")
        sys.exit(1)

    if args.search != "bfs" and args.search != "dfs":
        logging.error("Invalid argument for --search")
        sys.exit(1)

    valgrind_args = []

    if args.heap_size:
        size = utils.sizestr_to_int(args.heap_size)
        if size is None or size < 1:
            logging.error("Invalid heap size (parameter --heap-size)")
            sys.exit(1)
        valgrind_args.append("--heap-size={0}".format(size))

    if args.redzone_size:
        size = int(args.redzone_size)
        if size < 0:
            logging.error("Invalid redzone size")
            sys.exit(1)
        valgrind_args.append("--alloc-redzone-size={0}".format(size))

    if args.vgv:
        valgrind_args.append("--verbose={0}".format(args.vgv))

    if args.send_protocol not in ("full", "eager", "rendezvous", "dynamic"):
        threshold = parse_threshold(args.send_protocol)
        if threshold is None:
            logging.error("Invalid send protocol (parameter -S or --send-protocol)")
            sys.exit(1)
        args.send_protocol = "threshold"
        args.send_protocol_eager_threshold = threshold[0]
        args.send_protocol_rendezvous_threshold = threshold[1]
    else:
        args.send_protocol_eager_threshold = 0
        args.send_protocol_rendezvous_threshold = None

    if args.stdout_write and args.stdout != "capture":
        logging.error("--stdout-write is used but "
                      "stdout is not captured (--stdout option)")
        sys.exit(1)

    if args.stderr_write and args.stderr != "capture":
        logging.error("--stderr-write is used but "
                      "stderr is not captured (--stderr option)")
        sys.exit(1)

    return args, valgrind_args

def write_outputs(generator, stream_name, limit, file_prefix):
    if limit == "all":
        limit = None
    else:
        assert isinstance(limit, int)
    statespace = generator.statespace
    for pid in xrange(generator.process_count):
        outputs = list(statespace.get_all_outputs(stream_name, pid, limit))
        outputs.sort()
        for i, output in enumerate(outputs):
            with open("{0}-{1}-{2}".format(file_prefix, pid, i), "w") as f:
                    f.write(output)
        logging.info("{2} output(s) of pid {1} on {0} was written "
                     "(files '{3}-{1}-X')" \
                             .format(stream_name, pid, len(outputs), file_prefix))

def check_program(program):
    if not os.path.isfile(program):
        logging.error("File '%s' not found", program)
        sys.exit(1)
    if not os.access(program, os.X_OK):
        logging.error("File '%s' not executable", program)
        sys.exit(1)
    if not program.startswith(".") and not program.startswith("/"):
        program = os.path.join(".", program)
    return program

def main():
    args, valgrind_args = parse_args()
    run_args = [ check_program(args.program) ] + args.args
    generator = Generator(run_args,
                          args.p,
                          valgrind_args,
                          args)

    if platform.architecture()[0] != "64bit" or \
       platform.system() != "Linux":
           logging.error("Aislinn is not supported on this platform. "
                         "The current version supports only 64b Linux")
           sys.exit(1)

    logging.debug("Run args: %s", run_args)
    logging.debug("Valgrind args: %s", valgrind_args)

    logging.debug("stdout mode: %s, stderr mode: %s", args.stdout, args.stderr)

    if args.debug_profile:
        import cProfile
        import pstats
        pr = cProfile.Profile()
        pr.enable()
    if not generator.run():
        sys.exit(1)

    if generator.error_messages:
        for e in generator.error_messages:
            logging.info("Found error '%s'", e.name)
        logging.info("%s error(s) found", len(generator.error_messages))
    else:
        logging.info("No errors found")

    if args.debug_profile:
        pr.disable()
        with open("aislinn.stats", "w") as f:
            ps = pstats.Stats(pr, stream=f).sort_stats("cumulative")
            ps.print_stats()
        pr.dump_stats("aislinn.pstats")
        logging.info("Profile written into "
                     "'aislinn.stats' and 'aislinn.pstats'")

    if args.write_dot:
        generator.statespace.write_dot("statespace.dot")
        logging.info("Statespace graph written into 'statespace.dot'")

    if args.debug_statespace:
        generator.statespace.write("statespace.txt")
        logging.info("Statespace written into 'statespace.txt'")

    if args.report_type == "xml" or args.report_type == "html+xml":
        generator.create_report(args).write_xml("report.xml")
        logging.info("Report written into 'report.xml'")
    if args.report_type == "html" or args.report_type == "html+xml":
        if args.stdout_write:
            write_outputs(generator, STREAM_STDOUT, args.stdout_write, "stdout")
        if args.stderr_write:
            write_outputs(generator, STREAM_STDERR, args.stderr_write, "stderr")
        generator.create_report(args).write_html("report.html")
        logging.info("Report written into 'report.html'")

main()
