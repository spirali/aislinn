
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

    def test_typesize(self):
        self.program("typesize")
        self.execute(1, stdout="4 8 16 40\n")
        self.no_errors()

    def test_contiguous(self):
        output = "1.11\n2.22\n3.33\n4.44\n5.55\n" \
                 "6.66\n7.77\n8.88\n9.99\n10.101\n"
        self.program("contiguous")
        self.execute(2, stdout=output)
        self.no_errors()

    def test_vector(self):
        output = "0 1 2 3 4 5 10 11 12 13 14 15 16 17 18 19 20 21 26 27 28 29 "\
                 "30 31 32 33 34 35 36 37 42 43 44 45 46 47 48 49 50 51 52 53 "\
                 "58 59 60 61 62 63 -1 -1 \n"\
                 "0 1 2 3 4 5 -1 10 11 12 13 14 15 -1 16 17 18 19 20 21 -1 26 "\
                 "27 28 29 30 31 32 33 34 35 36 37 -1 42 43 44 45 46 47 -1 48 "\
                 "49 50 51 52 53 -1 58 59 \n"
        self.program("vector")
        self.execute(2, stdout=output)
        self.no_errors()

    def test_hvector(self):
        output = "0 1 2 3 4 5 10 11 12 13 14 15 16 17 18 19 20 21 26 27 28 29 "\
                 "30 31 32 33 34 35 36 37 42 43 44 45 46 47 48 49 50 51 52 53 "\
                 "58 59 60 61 62 63 -1 -1 \n"\
                 "0 1 2 3 4 5 -1 10 11 12 13 14 15 -1 16 17 18 19 20 21 -1 26 "\
                 "27 28 29 30 31 32 33 34 35 36 37 -1 42 43 44 45 46 47 -1 48 "\
                 "49 50 51 52 53 -1 58 59 \n"
        self.program("hvector")
        self.execute(2, stdout=output)
        self.no_errors()

    def test_indexed(self):
        output = "0 1 20 21 22 23 40 41 42 43 44 45 46 47 66 67 " \
                 "68 69 86 87 88 89 90 91 -1 -1 -1 -1 -1 -1 \n" \
                 "20 21 22 23 -1 0 1 42 43 44 45 -1 40 41 66 67 " \
                 "68 69 -1 46 47 88 89 90 91 -1 86 87 -1 -1 \n"
        output = None
        self.program("indexed")
        self.execute(2, "new", stdout=output)
        self.no_errors()
        self.execute(2, "old", stdout=output)
        self.no_errors()

    def test_uncommited(self):
        self.program("uncommited")
        self.execute(2, stdout="")
        self.single_error("uncommited")

    def test_typefree1(self):
        self.program("typefree1")
        self.execute(2, stdout="")
        self.single_error("invalidarg")

    def test_typefree2(self):
        self.program("typefree2")
        self.execute(2, stdout="")
        self.single_error("remove-buildin-type")


if __name__ == "__main__":
    unittest.main()
