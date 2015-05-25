import os
import subprocess
import shutil
import unittest
import xml.etree.ElementTree as xml
import sys

AISLINN_TESTS = os.path.dirname(os.path.abspath(__file__))
AISLINN_ROOT = os.path.dirname(AISLINN_TESTS)
AISLINN_BUILD = os.path.join(AISLINN_TESTS, "build")
AISLINN_REPORT_GALLERY = os.path.join(AISLINN_TESTS, "reports")
AISLINN_BIN = os.path.join(AISLINN_ROOT, "bin")

AISLINN = os.path.join(AISLINN_BIN, "aislinn")
AISLINN_CC = os.path.join(AISLINN_BIN, "aislinn-cc")
AISLINN_CPP = os.path.join(AISLINN_BIN, "aislinn-c++")

REPORT_GALLERY = False

sys.path.append(os.path.join(AISLINN_ROOT, "src", "aislinn"))
import base.controller
import base.bufserver

def set_to_sorted_list(s):
    lst = list(s)
    lst.sort()
    return lst


class TestCase(unittest.TestCase):

    category = None

    def setUp(self):
        self.test_name = None
        self.report = None
        self.program_instance = None
        self.output_instance = None
        self.reset_output_on_change = True
        self.counter = None
        self.bufserver_port = None
        self.bufserver_process = None
        self.controllers = []

    def tearDown(self):
        if self.bufserver_process:
            self.bufserver_process.terminate()
            self.bufserver_process.join()

        for c in self.controllers:
            c.kill()

    def read_report(self):
        filename = os.path.join(AISLINN_BUILD, "report.xml")
        return Report(filename)

    def check_error(self, error_key, **args):
        for error in self.report.errors:
            if error.key == error_key:
                for key, value in args.items():
                    a = error.element.get(key)
                    if a is None:
                        raise Exception(
                                "Cannot find attribute '{0}' for error '{1}'" \
                                        .format(key, error_key))
                    self.assertEquals(a, value)

    def program(self, test_name, files=None, **kw):
        if files is None:
            files = (os.path.join(AISLINN_TESTS, self.category, test_name + ".cpp"),)
        else:
            files = [ os.path.join(AISLINN_TESTS, self.category, test_name, n) for n in files ]
        self.program_instance = Program(files, **kw)
        self.program_instance.build()
        self.reset_output_on_change = True
        self.test_name = test_name
        self.counter = 0

    def reset_output(self):
        self.output_instance = Output()

    def output(self, pid, data):
        if self.reset_output_on_change:
            self.reset_output()
            self.reset_output_on_change = False
        self.output_instance.add(pid, data)

    def output_default(self, data):
        if self.reset_output_on_change:
            self.reset_output()
            self.reset_output_on_change = False
        self.output_instance.add_default(data)

    def execute(self,
            processes,
            args=(),
            error=None,
            vgv=None,
            verbose=None,
            stdout=None,
            check_output=True,
            send_protocol="full",
            heap_size=None,
            redzone_size=None,
            profile=False,
            ):
        aislinn_args = { "report-type" : "xml",
                         "verbose" : 0,
                         "stderr-write" : "1000" }

        if REPORT_GALLERY and error:
            aislinn_args["report-type"] = "html+xml"

        if error:
            check_output = False

        if vgv:
            aislinn_args["vgv"] = vgv

        if verbose:
            aislinn_args["verbose"] = verbose

        if send_protocol:
            aislinn_args["send-protocol"] = send_protocol

        if heap_size:
            aislinn_args["heap-size"] = heap_size

        if redzone_size:
            aislinn_args["redzone-size"] = redzone_size

        if profile:
            aislinn_args["profile"] = None

        if stdout is not None:
            aislinn_args["stdout"] = "print"
            check_output = False

        if aislinn_args.get("stdout") in (None, "capture"):
            aislinn_args["stdout-write"] = "1000"

        if isinstance(args, str):
            args = args.split()

        # Run ---------------------------
        result_stdout, result_stderr = \
                self.program_instance.run(aislinn_args, processes, args)


        report = self.read_report()
        self.report = report

        # Check errors
        found_errors = [ e.key for e in report.errors ]
        if error is None and found_errors:
            raise Exception("No errors expected, found: " + repr(found_errors))
        if isinstance(error, str):
            error = [ error ]
        if error and set(error) != set(found_errors):
            raise Exception("Different errors expected. Expected {0}, got {1}" \
                    .format(error, found_errors))

        # Stderr
        self.assertEquals(result_stderr, "")

        # Stdout
        if stdout is not None:
            if callable(stdout):
                self.assertTrue(stdout(result_stdout))
            else:
                self.assertEquals(result_stdout, stdout)
        else:
            self.assertEquals(result_stdout, "")

        if check_output:
            self.check_output(report, processes)

        if REPORT_GALLERY and error:
            filename = "{0.category}-{0.test_name}-{0.counter}-{1}.html" \
                    .format(self, "_".join(error).replace("/", "."))
            os.rename(os.path.join(AISLINN_BUILD, "report.html"),
                      os.path.join(AISLINN_REPORT_GALLERY, filename))

        self.reset_output_on_change = True
        self.counter += 1

    def check_output(self, report, processes):
        if self.output_instance is None:
            self.reset_output()
        for pid in xrange(processes):
            expected_outputs = set(self.output_instance.get_output_for_process(pid))
            program_outputs = report.get_outputs(pid)
            if expected_outputs != program_outputs:
                raise Exception("Unexpected or missing outputs for process {0}:\n"
                                "Expected outputs: {1}\n"
                                "Program outputs: {2}\n"
                                "Extra outputs: {3}\n"
                                "Missing outputs: {4}\n" \
                                    .format(pid,
                                            set_to_sorted_list(expected_outputs),
                                            set_to_sorted_list(program_outputs),
                                            set_to_sorted_list(program_outputs - expected_outputs),
                                            set_to_sorted_list(expected_outputs - program_outputs)))

    def controller(self, args=(), verbose=False, profile=False):
        self.assertTrue(self.program_instance is not None)
        self.report = None
        c = self.program_instance.controller(
                args, verbose, profile, self.bufserver_port)
        self.controllers.append(c)
        return c

    def start_bufserver(self, clients_count):
        if self.bufserver_process is not None:
            return
        self.bufserver_process, \
            self.bufserver_port \
                = base.bufserver.start_process(clients_count)

    def connect_to_bufserver(self):
        assert self.bufserver_process
        return base.bufserver.connect(self.bufserver_port)


def cleanup_build_dir():
    if os.path.isdir(AISLINN_BUILD):
        for item in os.listdir(AISLINN_BUILD):
            path = os.path.join(AISLINN_BUILD, item)
            if os.path.isfile(path):
                os.unlink(path)
            else:
                shutil.rmtree(path)
    else:
        os.makedirs(AISLINN_BUILD)

def run(args,
        cwd=None):
    p = subprocess.Popen(args,
                         cwd=cwd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    return (p.returncode, stdout, stderr)

def check_prefix(prefix):
    def fn(value):
        if not value.startswith(prefix):
            return "Expected prefix " + prefix
    return fn

def run_and_check(args,
                  cwd=None):
    r_exitcode, r_stdout, r_stderr = run(args, cwd)
    if r_exitcode != 0 or r_stdout or r_stderr:
        raise Exception("\nprogram: {0}\nstdout:\n{1}stderr:\n{2}\n"
                            .format(args, r_stdout, r_stderr))


class Output:

    def __init__(self):
        self.default = None
        self.contents = {}

    def add_default(self, values):
        if isinstance(values, str):
            values = [values]

        if self.default is not None:
            self.default += values
        else:
            self.default = values

    def add(self, pid, values):
        if isinstance(values, str):
            values = [values]
        if pid in self.contents:
            self.contents[pid] += values
        else:
            self.contents[pid] = values

    def get_output_for_process(self, pid):
        values = self.contents.get(pid)
        if values is not None:
            return values
        elif self.default:
            return self.default
        else:
            return [""]


class Program:

    def __init__(self, files):
        self.files = tuple(files)

    def build(self):
        cleanup_build_dir()
        args = (AISLINN_CPP,
                "-g",
                "-O3") + self.files
        run_and_check(args, cwd=AISLINN_BUILD)

    def run(self, aislinn_args, processes, program_args):
        run_args = [ AISLINN, "-p={0}".format(processes) ] + \
                   [ ("--{0}={1}" if value is not None else "--{0}").format(name, value)
                     for name, value in aislinn_args.items() ]
        run_args.append("./a.out")
        run_args += list(program_args)
        exitcode, stdout, stderr = run(run_args, cwd=AISLINN_BUILD)
        if exitcode != 0:
            raise Exception("Nonzero exit code\n"
                            "exitcode={0}\nstdout={1}\nstderr={2}" \
                                    .format(exitcode, stdout, stderr))
        return stdout, stderr


    def controller(self, args, verbose, profile, bufserver_port):
        controller = base.controller.Controller(("./a.out",) + args, AISLINN_BUILD)
        controller.profile = profile
        controller.buffer_server_port = bufserver_port
        if verbose:
           controller.valgrind_args = ("--verbose={0}".format(verbose),)
        return controller


class Error(object):

    def __init__(self, element):
        self.element = element

    @property
    def key(self):
        return self.element.get("key")

    @property
    def name(self):
        return self.element.get("name")

    @property
    def pid(self):
        return self.find_int("pid")

    def find_int(self, name):
        return int(self.element.find(name).text)

    def __repr__(self):
        return "E({0})".format(self.name)


class Report:

    def __init__(self, filename):
        self.root = xml.parse(filename).getroot()
        self.errors = map(Error, self.root.findall("error"))

    @property
    def number_of_nodes(self):
        return int(self.root.find("analysis-info").find("nodes").text)

    @property
    def determinisic_nonfreed_memory(self):
        return int(self.root.find("analysis-info") \
                .find("deterministic-non-freed-memory").text)

    def get_icounts(self, name):
        return map(str, self.root.find("profile").find("instructions").find(name).text.split())

    def get_stream(self, name):
        for stream in self.root.find("streams").findall("stream"):
            if stream.get("name") == name:
                return stream

    def get_outputs(self, pid):
        for process in self.get_stream("<stdout>").findall("process"):
            if int(process.get("pid")) == pid:
                return set(o.text if o.text is not None else ""
                           for o in process.findall("output"))

