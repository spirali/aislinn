
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
        errmsg = "==AN== ERROR: Invalid number of processes (parameter -p)\n"
        self.execute(-1, exitcode=1, stderr=errmsg)
        self.execute(0, exitcode=1, stderr=errmsg)

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

    def test_invalid_args(self):
        self.program("args")
        args = [ "isend_rank_1",
                 "isend_rank_2",
                 "isend_rank_3",
                 "irecv_rank",
                 "irecv_tag",
                 "send_tag",
                 "send_tag_2",
                 "isend_count",
                 "irecv_count",
                 "irecv_datatype" ]

        for arg in args:
            self.execute(2, (arg,))
            self.single_error("invalidarg", pid=0)

    def test_globals(self):
        self.program("globals")
        self.execute(2)
        self.no_errors()

if __name__ == "__main__":
    unittest.main()
