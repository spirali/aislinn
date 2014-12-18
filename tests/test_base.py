
from utils import TestCase
import unittest

class BaseTests(TestCase):

    category = "base"

    def test_helloworld(self):
        self.program("helloworld")

        self.execute(1, error="nompicall", check_output=False)
        self.execute(3, error="nompicall", check_output=False)

    def test_helloworld2(self):
        self.program("helloworld2")

        self.execute(1, check_output=False)
        self.assertEquals(self.report.number_of_nodes, 3)

        self.execute(3, check_output=False)
        self.assertEquals(self.report.number_of_nodes, 5)

    def test_exitcode(self):
        self.program("exitcode")
        self.execute(1, error="exitcode")
        self.check_error("exitcode", pid="0", exitcode="21")
        self.assertEquals(self.report.number_of_nodes, 3)

    """
    def test_arg_p(self):
        self.program("exitcode")
        errmsg = "==AN== ERROR: Invalid number of processes (parameter -p)\n"
        self.execute(-1, exitcode=1, stderr=errmsg)
        self.execute(0, exitcode=1, stderr=errmsg)
    """

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
            self.execute(2, arg, error="invalidarg")
            self.check_error("invalidarg", pid="0")

    def test_globals(self):
        self.program("globals")
        self.execute(2)

    def test_typesize(self):
        self.program("typesize")
        self.execute(1, stdout="4 8 16 40\n")

    def test_contiguous(self):
        output = "1.11\n2.22\n3.33\n4.44\n5.55\n" \
                 "6.66\n7.77\n8.88\n9.99\n10.101\n"
        self.program("contiguous")
        self.execute(2, stdout=output)

    def test_vector(self):
        output = "0 1 2 3 4 5 10 11 12 13 14 15 16 17 18 19 20 21 26 27 28 29 "\
                 "30 31 32 33 34 35 36 37 42 43 44 45 46 47 48 49 50 51 52 53 "\
                 "58 59 60 61 62 63 -1 -1 \n"\
                 "0 1 2 3 4 5 -1 10 11 12 13 14 15 -1 16 17 18 19 20 21 -1 26 "\
                 "27 28 29 30 31 32 33 34 35 36 37 -1 42 43 44 45 46 47 -1 48 "\
                 "49 50 51 52 53 -1 58 59 \n"
        self.program("vector")
        self.execute(2, stdout=output)

    def test_struct(self):
        output = ("0 0 1 1 inf\n"
                  "1 1 2 2 5\n"
                  "2 2 3 3 2.5\n"
                  "0 3 4 4 1.66667\n"
                  "1 4 5 5 1.25\n"
                  "2 5 6 6 1\n"
                  "0 6 7 0 0.833333\n"
                  "1 7 8 1 0.714286\n"
                  "2 8 9 2 0.625\n"
                  "0 9 10 3 0.555556\n")
        self.program("struct")
        self.execute(2, stdout=output)

    def test_hvector(self):
        output = "0 1 2 3 4 5 10 11 12 13 14 15 16 17 18 19 20 21 26 27 28 29 "\
                 "30 31 32 33 34 35 36 37 42 43 44 45 46 47 48 49 50 51 52 53 "\
                 "58 59 60 61 62 63 -1 -1 \n"\
                 "0 1 2 3 4 5 -1 10 11 12 13 14 15 -1 16 17 18 19 20 21 -1 26 "\
                 "27 28 29 30 31 32 33 34 35 36 37 -1 42 43 44 45 46 47 -1 48 "\
                 "49 50 51 52 53 -1 58 59 \n"
        self.program("hvector")
        self.execute(2, stdout=output)

    def test_indexed(self):
        output = "0 1 20 21 22 23 40 41 42 43 44 45 46 47 66 67 " \
                 "68 69 86 87 88 89 90 91 -1 -1 -1 -1 -1 -1 \n" \
                 "20 21 22 23 -1 0 1 42 43 44 45 -1 40 41 66 67 " \
                 "68 69 -1 46 47 88 89 90 91 -1 86 87 -1 -1 \n"
        self.program("indexed")
        self.execute(2, "new", stdout=output)
        self.execute(2, "old", stdout=output)

    def test_uncommited(self):
        self.program("uncommited")
        self.execute(2, error="uncommited")

    def test_typefree1(self):
        self.program("typefree1")
        self.execute(2, error="invalidarg")

    def test_typefree2(self):
        self.program("typefree2")
        self.execute(2, error="remove-buildin-type")

    def test_group(self):
        self.program("group")
        self.execute(3)

    def test_group2(self):
        self.program("group2")
        self.execute(4)

    def test_finalized(self):
        self.program("finalized")
        self.execute(1)

    def test_initialized(self):
        self.program("initialized")
        self.execute(1)

    def test_keyval(self):
        output="DELETE 2\nCOPY 4\nDELETE 1\nDELETE 3\nDELETE 4\n"
        self.program("keyval")
        self.execute(1, stdout=output)

    def test_keyval2(self):
        self.program("keyval2")
        self.execute(1, stdout="DELETE 2\nDELETE 1\nDELETE 3\n")

    def test_keyval3(self):
        self.program("keyval3")
        self.execute(1, stdout="DELETE 1\n")
        self.execute(1, "error", error="invalidarg")

    def test_print(self):
        self.program("print")
        self.output_default("Line1\nEnd\n")
        self.output(1, "Line1\n0\n2\nEnd\n")
        self.output(1, "Line1\n2\n0\nEnd\n")
        self.execute(3)

        self.reset_output()
        self.output_default("Line1\nEnd\n")
        self.output(1, "Line1\n0\n2\n3\nEnd\n")
        self.output(1, "Line1\n0\n3\n2\nEnd\n")
        self.output(1, "Line1\n2\n0\n3\nEnd\n")
        self.output(1, "Line1\n2\n3\n0\nEnd\n")
        self.output(1, "Line1\n3\n0\n2\nEnd\n")
        self.output(1, "Line1\n3\n2\n0\nEnd\n")
        self.execute(4)

    def test_print_big(self):
        self.program("print_big")
        self.output(0, "abcd" * (1024 * 1024 * 10 // 4) + "\n")
        self.execute(1)

    def test_processor_name(self):
        self.program("processor_name")
        self.output(0, "Processor-0\n")
        self.output(1, "Processor-1\n")
        self.execute(2, "1000")
        # Test buffer smaller than MPI_MAX_PROCESSOR_NAME
        self.execute(2, "100", error="invalid-name-buffer")

if __name__ == "__main__":
    unittest.main()
