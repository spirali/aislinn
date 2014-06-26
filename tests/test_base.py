
from utils import TestCase
import unittest

class BaseTests(TestCase):

    category = "base"

    def test_helloworld(self):
        self.program("helloworld")

        self.execute(1)
        self.single_error("nompicall")

        self.execute(3)
        self.single_error("nompicall")

    def test_helloworld2(self):
        self.program("helloworld2")

        self.execute(1)
        self.no_errors()
        self.assertEquals(self.report.number_of_nodes, 2)

        self.execute(3)
        self.no_errors()
        self.assertEquals(self.report.number_of_nodes, 4)

    def test_exitcode(self):
        self.program("exitcode")
        self.execute(1)
        self.exit_code_error(0, 21)
        self.assertEquals(self.report.number_of_nodes, 2)

    def test_arg_p(self):
        self.program("exitcode")
        self.execute(-1, exitcode=1, stderr="Invalid number of processes\n")
        self.execute(0, exitcode=1, stderr="Invalid number of processes\n")

    def test_heapsize(self):
        self.program("malloc")

        self.execute(1, ("100",))
        self.no_errors()


        self.execute(1, ("100",), heapsize="1M")
        self.no_errors()

        self.execute(1,
                     ("10000000",),
                     heapsize="1M")
        self.single_error("heaperror")

        self.execute(1, ("10000000",), heapsize="100M")
        self.no_errors()

    def test_malloc_free(self):
        self.program("mallocfree")
        self.execute(1)
        self.no_errors()

if __name__ == "__main__":
    unittest.main()
