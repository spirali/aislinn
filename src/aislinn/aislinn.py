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


from mpi.generator import Generator
import base.utils as utils
import argparse
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
    parser.add_argument("--heapsize",
                        metavar="SIZE",
                        type=str,
                        help="Maximal size of heap")
    parser.add_argument("-S", "--send-protocol",
                        metavar="VALUE",
                        type=str,
                        help="Standard send protocol.",
                        default="full")
    parser.add_argument("--output",
                        metavar="TYPE",
                        type=str,
                        help="Output type: xml, html, none",
                        default="html")
    parser.add_argument("--stats",
                       metavar="TICKS",
                       type=int,
                       default=None)
    parser.add_argument("--write-dot",
                       action="store_true")
    parser.add_argument("--debug-under-valgrind",
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

    logging.basicConfig(format="==AN== %(levelname)s: %(message)s",
                        level=level)

    if args.p <= 0:
        logging.error("Invalid number of processes (parameter -p)")
        sys.exit(1)

    if args.output not in ("xml", "html", "none"):
        logging.error("Invalid output type (parameter --output)")
        sys.exit(1)

    valgrind_args = []

    if args.heapsize:
        size = utils.sizestr_to_int(args.heapsize)
        if size is None or size < 1:
            logging.error("Invalid heap size (parameter --heapsize)")
            sys.exit(1)
        valgrind_args.append("--heapsize={0}".format(size))

    if args.vgv:
        valgrind_args.append("--verbose={0}".format(args.vgv))

    if args.send_protocol not in ("full", "eager", "randezvous", "dynamic"):
        threshold = parse_threshold(args.send_protocol)
        if threshold is None:
            logging.error("Invalid send protocol (parameter -S or --send-protocol)")
            sys.exit(1)
        args.send_protocol = "threshold"
        args.send_protocol_eager_threshold = threshold[0]
        args.send_protocol_randezvous_threshold = threshold[1]
    else:
        args.send_protocol_eager_threshold = 0
        args.send_protocol_randezvous_threshold = None

    return args, valgrind_args

def main():
    args, valgrind_args = parse_args()

    run_args = [ args.program ] + args.args
    generator = Generator(run_args,
                          valgrind_args,
                          args)

    if platform.architecture()[0] != "64bit" or \
       platform.system() != "Linux":
           logging.error("Aislinn is not supported on this platform. "
                         "The current version supports only 64b Linux")
           sys.exit(1)


    logging.debug("Run args: %s", run_args)
    logging.debug("Valgrind args: %s", valgrind_args)

    if not generator.run(args.p):
        sys.exit(1)

    if args.write_dot:
        generator.statespace.write_dot("statespace.dot")
        logging.info("Statespace graph written into 'statespace.dot'")

    if args.output == "xml":
        generator.create_report().write_xml("report.xml")
        logging.info("Report written into 'report.xml'")
    elif args.output == "html":
        generator.create_report().write_html("report.html")
        logging.info("Report written into 'report.html'")
    if generator.error_messages:
        logging.info("%s error(s) found", len(generator.error_messages))
    else:
        logging.info("No errors found")

main()
