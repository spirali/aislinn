import os
import subprocess
import shutil
import unittest
import xml.etree.ElementTree as xml
import sys

AISLINN_TESTS = os.path.dirname(os.path.abspath(__file__))
AISLINN_ROOT = os.path.dirname(AISLINN_TESTS)
AISLINN_BUILD = os.path.join(AISLINN_TESTS, "build")
AISLINN_BIN = os.path.join(AISLINN_ROOT, "bin")

AISLINN = os.path.join(AISLINN_BIN, "aislinn")
AISLINN_CC = os.path.join(AISLINN_BIN, "aislinn-cc")
AISLINN_CPP = os.path.join(AISLINN_BIN, "aislinn-c++")

sys.path.append(os.path.join(AISLINN_ROOT, "src", "aislinn"))
import base.controller

class TestCase(unittest.TestCase):

    category = None

    def setUp(self):
        self.report = None
        self.program_instance = None

    def read_report(self):
        filename = os.path.join(AISLINN_BUILD, "report.xml")
        self.report = Report(filename)

    def no_errors(self):
        if self.report is None:
            self.read_report()
        if len(self.report.errors) != 0:
            names = [ e.name for e in self.report.errors ]
            raise AssertionError("No error expected, got " + repr(names))

    def single_error(self, error_name, rank=None):
        if self.report is None:
            self.read_report()
        errors = self.report.errors
        self.assertEquals(len(errors), 1)
        error = errors[0]
        self.assertEquals(error.name, error_name)
        if rank is not None:
            self.assertEquals(error.rank, rank)
        return error

    def check_child(self, element, name, value):
        child = element.find(name)
        self.assertTrue(child is not None,
                        "Node {0} has not child {1}".format(element, name))
        self.assertEquals(element.find(name).text, str(value))

    def exit_code_error(self, rank, exitcode=0):
        if self.report is None:
            self.read_report()
        error = self.single_error("exitcode", rank=rank)
        self.assertEquals(error.find_int("exitcode"), exitcode)

    def program(self, test_name, files=None, **kw):
        if files is None:
            files = (os.path.join(AISLINN_TESTS, self.category, test_name + ".cpp"),)
        else:
            files = [ os.path.join(AISLINN_TESTS, self.category, test_name, n) for n in files ]
        self.program_instance = Program(files, **kw)

    def execute(self, *args, **kw):
        self.assertTrue(self.program_instance is not None)
        self.report = None
        self.program_instance.run(*args, **kw)

    def controller(self, verbose=False):
        self.assertTrue(self.program_instance is not None)
        self.report = None
        return self.program_instance.controller(verbose)


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

def cleanup_report():
    reportfile = os.path.join(AISLINN_BUILD, "report.xml")
    if os.path.isfile(reportfile):
        os.unlink(reportfile)

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
                  cwd=None,
                  exitcode=0,
                  stdout="",
                  stderr=""):
    def raise_exception(message):
        raise Exception(message +
                "\nprogram: {0}\nstdout:\n{1}stderr:\n{2}\n"
                .format(args, r_stdout, r_stderr))

    r_exitcode, r_stdout, r_stderr = run(args, cwd)
    if exitcode != r_exitcode:
        raise_exception("Exitcode {0} excepted but got {1}".format(exitcode,
                                                                   r_exitcode))
    if stdout is not None:
        if isinstance(stdout, str):
            if stdout != r_stdout:
                if stdout == "":
                    stdout = ">>> empty <<<"
                raise_exception("Got unexpected stdout.\n"
                                "Expected stdout:\n{0}".format(stdout))
        else:
            r = stdout(r_stdout)
            if r is not None:
                raise_exception("Expected stdout: " + r)

    if stderr is not None:
        if isinstance(stderr, str):
            if stderr != r_stderr:
                if stderr == "":
                    stderr = ">>> empty <<<"
                raise_exception("Got unexpected stderr.\n"
                                "Expected stderr:\n{0}".format(stderr))
        else:
            r = stderr(r_stderr)
            if r is not None:
                raise_exception("Expected stderr: " + r)


class Program:

    def __init__(self, files):
        self.files = tuple(files)
        self.is_built = False

    def build(self):
        cleanup_build_dir()
        args = (AISLINN_CPP,
                "-g",
                "-O3") + self.files
        run_and_check(args, cwd=AISLINN_BUILD)
        self.is_built = True

    def make_args(self, processes, args,
                  heapsize=None,
                  send_protocol=None):
        run_args = [ AISLINN,
                    "--output=xml",
                    "--verbose=0",
                    "-p={0}".format(processes) ]

        if heapsize is not None:
            run_args.append("--heapsize={0}".format(heapsize))
        if send_protocol is not None:
            run_args.append("--send-protocol={0}".format(send_protocol))
        run_args.append("./a.out")
        run_args += list(args)
        return run_args

    def run(self, processes, args=(), exitcode=0, stdout=None, stderr="", **kw):
        if not self.is_built:
            self.build()
        else:
            cleanup_report()
        run_and_check(self.make_args(processes, args, **kw),
                      AISLINN_BUILD,
                      exitcode,
                      stdout,
                      stderr)

    def controller(self, verbose):
        if not self.is_built:
            self.build()
        controller = base.controller.Controller(("./a.out",), AISLINN_BUILD)
        if verbose:
           controller.valgrind_args = ("--verbose=1",)
        return controller

class Error(object):

    def __init__(self, element):
        self.element = element

    @property
    def name(self):
        return self.element.get("name")

    @property
    def rank(self):
        return self.find_int("rank")

    def find_int(self, name):
        return int(self.element.find(name).text)

class Report:

    def __init__(self, filename):
        self.root = xml.parse(filename).getroot()
        self.errors = map(Error, self.root.findall("error"))

    @property
    def number_of_nodes(self):
        return int(self.root.find("info").find("nodes").text)
