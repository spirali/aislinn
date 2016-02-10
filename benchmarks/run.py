import time
import subprocess
import sys

DEV_NULL = open("/dev/null", "w")

RUN_ARGS = {
    "aislinn": "../bin/aislinn --verbose=0",
}


def run_silent(command):
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode:
        print "Command:", command
        print "Stdout:", stdout
        print "Stderr", stderr
        raise Exception("Benchmark failed")


class Benchmark(object):

    def __init__(self, name):
        self.name = name
        self.command = None
        self.pre_command = None

    def run(self):
        command = self.command.format(**RUN_ARGS).split()
        start = time.time()
        run_silent(command)
        end = time.time()
        return end - start


def init():
    benchmarks = []

    b = Benchmark("heatflow-A-2")
    b.command = "{aislinn} -p 2 ./heatflow 400 400 70 2000"
    benchmarks.append(b)

    b = Benchmark("heatflow-A-4")
    b.command = "{aislinn} -p 4 ./heatflow 400 400 70 2000"
    benchmarks.append(b)

    b = Benchmark("heatflow-B-2")
    b.command = "{aislinn} -p 2 ./heatflow 1000 1000 50 2000"
    benchmarks.append(b)

    b = Benchmark("heatflow-B-4")
    b.command = "{aislinn} -p 4 ./heatflow 1000 1000 50 2000"
    benchmarks.append(b)

    b = Benchmark("workers-A-6")
    b.command = "{aislinn} -p 6 ./workers 10 80"
    benchmarks.append(b)

    b = Benchmark("workers-B-4")
    b.command = "{aislinn} -p 4 ./workers 10 120"
    benchmarks.append(b)

    b = Benchmark("bzip2")
    b.command = "{aislinn} -p 1 /bin/bzip2 -f -k testfile"
    benchmarks.append(b)

    b = Benchmark("graphviz")
    b.command = "{aislinn} -p 1 /usr/bin/dot -Tpng test.dot -o /dev/null"
    benchmarks.append(b)

    return benchmarks


def main():
    benchmarks = init()
    argv = sys.argv
    if len(argv) > 2:
        print "Invalid args"
    elif len(argv) == 2:
        name = argv[1]
        benchmarks = [b for b in benchmarks if name in b.name]

    if not benchmarks:
        print "No tests selected"

    for b in benchmarks:
        print b.name, "...",
        sys.stdout.flush()
        print "{:0.2f}".format(b.run())


if __name__ == "__main__":
    main()
