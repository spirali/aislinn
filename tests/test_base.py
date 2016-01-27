
from utils import TestCase
import unittest


class BaseTests(TestCase):

    category = "base"

    def test_helloworld(self):
        self.program("helloworld")

        self.execute(1, error="mpi/no-mpi-call", check_output=False)
        self.execute(3, error="mpi/no-mpi-call", check_output=False)

    def test_helloworld2(self):
        self.program("helloworld2")

        self.execute(1, check_output=False)
        self.assertEquals(self.report.number_of_nodes, 3)

        self.execute(3, check_output=False)
        self.assertEquals(self.report.number_of_nodes, 3)

    def test_exitcode(self):
        self.program("exitcode")
        self.execute(1, error="base/exitcode")
        self.check_error("exitcode", pid="0", exitcode="21")
        self.assertEquals(self.report.number_of_nodes, 3)

    def test_exitcode_nompi(self):
        self.program("exitcode_nompi")
        self.execute(1, error="base/exitcode")
        self.check_error("exitcode", pid="0", exitcode="21")

    def test_invalid_args(self):
        self.program("args")
        args = [("isend_rank_1", "mpi/invalid-arg/rank"),
                ("isend_rank_2", "mpi/invalid-arg/rank"),
                ("isend_rank_3", "mpi/invalid-arg/rank"),
                ("irecv_rank", "mpi/invalid-arg/rank"),
                ("irecv_tag", "mpi/invalid-arg/tag"),
                ("send_tag", "mpi/invalid-arg/tag"),
                ("send_tag_2", "mpi/invalid-arg/tag"),
                ("isend_count", "mpi/invalid-arg/count"),
                ("irecv_count", "mpi/invalid-arg/count"),
                ("irecv_datatype", "mpi/invalid-arg/datatype")]

        for arg, error in args:
            self.execute(2, arg, error=error)
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

    def test_struct_invalid(self):
        self.program("struct_invalid")
        self.execute(1, "count", error="mpi/invalid-arg/count")
        self.execute(1, "sizes", error="mpi/invalid-arg/length")

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

    def test_indexed_bottom(self):
        output = "0 1 2 3 4 0 0 0 0 0 0 0 0 0 " \
                 "14 15 16 17 18 19 20 21 0 0 0 0 0 0 0 0 \n"
        self.program("indexed_bottom")
        self.execute(2, stdout=output)

    def test_indexed_intersect(self):
        output = "0 1 2 3 4 5 6 7 8 0 0 0 12 13 0 0 16 17 " \
                 "0 0 0 0 0 0 0 0 0 0 0 0 \n"
        self.program("indexed_intersect")
        self.execute(2, "4", stdout=output)
        self.execute(2, "0", error="mpi/invalid-recv-buffer")

    def test_uncommited(self):
        self.program("uncommited")
        self.execute(2, error="mpi/invalid-arg/uncommited-datatype")

    def test_typefree1(self):
        self.program("typefree1")
        self.execute(2, error="mpi/invalid-arg/datatype")

    def test_typefree2(self):
        self.program("typefree2")
        self.execute(2, error="mpi/removing-buildin-datatype")

    def test_group(self):
        self.program("group")
        self.execute(3)

    def test_group2(self):
        self.program("group2")
        self.execute(4)

    def test_group_excl(self):
        self.program("group_excl")
        self.execute(4)
        self.execute(2, error="mpi/invalid-arg/rank")

    def test_group_excl2(self):
        self.program("group_excl2")
        self.execute(3, error="mpi/invalid-arg/non-unique-values")

    def test_group_free_invalid(self):
        self.program("group_free_invalid")
        self.execute(1, error="mpi/invalid-arg/group")

    def test_finalized(self):
        self.program("finalized")
        self.execute(1)

    def test_initialized(self):
        self.program("initialized")
        self.execute(1)

    def test_keyval(self):
        output = "DELETE 2\nCOPY 4\nDELETE 1\nDELETE 3\nDELETE 4\n"
        self.program("keyval")
        self.execute(1, stdout=output)

    def test_keyval2(self):
        self.program("keyval2")
        self.execute(1, stdout="DELETE 2\nDELETE 1\nDELETE 3\n")

    def test_keyval3(self):
        self.program("keyval3")
        self.execute(1, stdout="DELETE 1\n")
        self.execute(1, "error", error="mpi/invalid-arg/communicator")
        self.execute(1, "free_error", error="mpi/invalid-arg/keyval")
        self.execute(
            1, "delete_attr_error", error="mpi/invalid-arg/attribute")
        self.execute(1, "exit_error", error="base/exit-in-callback")
        self.execute(1, "comm_error", error="mpi/communication-in-callback")

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
        self.execute(2, "100", error="mpi/invalid-processor-name-buffer")

    def test_request_leak(self):
        self.program("request_leak")
        self.execute(1, "send", error="mpi/pending-request")
        self.execute(1, "recv1", error="mpi/pending-request")
        self.execute(1, "recv2", error="mpi/pending-request")

    def test_request_invalid(self):
        self.program("request_invalid")
        self.execute(1, "wait", error="mpi/invalid-arg/request")
        self.execute(1, "waitall", error="mpi/invalid-arg/request")
        self.check_error(
            "mpi/invalid-arg/request", pid="0", index="1", value="123")
        self.execute(
            1, "start", error="mpi/invalid-arg/not-persistent-request")
        self.execute(
            1, "start-active",
            error="mpi/invalid-arg/already-active-persistent-request")

    def test_message_leak(self):
        self.program("message_leak")
        self.execute(2, error="mpi/pending-message")

    def test_double_finalize(self):
        self.program("double_finalize")
        self.execute(1, error="mpi/double-finalize")

    def test_abort(self):
        self.program("abort")
        self.execute(1, "before", error="mpi/init-missing")
        self.execute(1, "after", error="mpi/abort")


if __name__ == "__main__":
    unittest.main()
