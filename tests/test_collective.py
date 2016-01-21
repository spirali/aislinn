
from utils import TestCase
import unittest

class CollectiveTests(TestCase):

    category = "collective"

    def test_invalid(self):
        self.program("invalid")

        self.execute(2, "gatherv_root", error="mpi/invalid-arg/rank")
        self.execute(2, "gatherv_sendcount", error="mpi/invalid-arg/count")
        self.execute(2, "reduce_op", error="mpi/invalid-arg/operation")

    def test_ibarrier(self):
        self.program("ibarrier")

        self.output(1, "a = 0; b = 200\n")
        self.output(1, "a = 200; b = 0\n")
        self.execute(3, "a")

        self.reset_output()
        self.output(1, "a = 0; b = 200\n")
        self.execute(3, "b")

    def test_barrier(self):
        self.program("barrier")
        self.output(1, "a = 0; b = 200\n")
        self.execute(3)

    def test_gatherv(self):
        self.program("gatherv")

        self.output(0, "OUT1: 100 101\nOUT2: 100 101\n")
        self.execute(1, "gatherv")
        self.execute(1, "iwaitall")
        self.execute(1, "iwait")

        self.reset_output()
        self.output(1, "OUT1: 100 101 102 103 104 105 200 201 202 203 204 300 301 302 303\n"\
                           "OUT2: 100 101 102 103 104 105 200 201 202 203 204 300 301 302 303\n")

        self.execute(3, "gatherv")
        self.execute(3, "iwaitall")
        self.execute(3, "iwait")
        self.execute(3, "mismatch", error="mpi/collective-mismatch/root")
        self.execute(3, "imismatch", error="mpi/collective-mismatch/root")

    def test_allgatherv(self):
        self.program("allgatherv")

        self.output(0, "OUT1: 100 101\nOUT2: 100 101\n")
        self.execute(1)

        self.reset_output()
        self.output_default("OUT1: 100 101 102 103 104 105 200 201 202 203 204 300 301 302 303\n"\
                                "OUT2: 100 101 102 103 104 105 200 201 202 203 204 300 301 302 303\n")
        self.execute(3)

    def test_igather(self):
        self.program("igather")
        self.output(0, "OUT1: 100 101 102 103 200 201 202 203 300 301 302 303\n" \
                           "OUT2: 1000 1001 1002 1003 2000 2001 2002 2003 3000 3001 3002 3003\n")
        self.execute(3, "0")

        self.reset_output()
        self.output(1, "OUT1: 100 101 102 103 200 201 202 203 300 301 302 303\n" \
                           "OUT2: 1000 1001 1002 1003 2000 2001 2002 2003 3000 3001 3002 3003\n")

        self.execute(3, "1")

        self.reset_output()
        self.output(2, "OUT1: 100 101 102 103 200 201 202 203 300 301 302 303\n" \
                           "OUT2: 1000 1001 1002 1003 2000 2001 2002 2003 3000 3001 3002 3003\n")
        self.execute(3, "2")

    def test_bcast(self):
        def set_output(root):
            self.reset_output()
            for pid in xrange(3):
                self.output(pid, "{1} OUT1: {0}00 {0}01 {0}02 {0}03\n"
                                     "{1} OUT2: {0}000 {0}001 {0}002 {0}003\n".format(root, pid))
        self.program("bcast")

        set_output(1)
        self.execute(3, "0")
        set_output(2)
        self.execute(3, "1")
        set_output(3)
        self.execute(3, "2")

    def test_iscatterv(self):
        self.program("iscatterv")

        self.output(0, "0/2:OUT1: 100 200\n" \
                           "0/2:OUT2: 100 200\n")
        self.execute(1, "waitall")
        self.execute(1, "wait")

        self.reset_output()
        self.output(0, "0/6:OUT1: 100 200 300 400 500 600\n" \
                           "0/6:OUT2: 100 200 300 400 500 600\n")
        self.output(1, "1/5:OUT1: 200 300 400 500 600\n" \
                           "1/5:OUT2: 200 300 400 500 600\n")
        self.output(2, "2/4:OUT1: 300 400 500 600\n" \
                           "2/4:OUT2: 300 400 500 600\n")
        self.execute(3, "waitall")
        self.execute(3, "wait")

    def test_iscatter(self):
        self.program("iscatter")

        self.output(0, "0: OUT1: 100 200 300 400\n"
                           "0 OUT2: 1000 2000 3000 4000\n")
        self.output(1, "1: OUT1: 500 600 700 800\n" \
                           "1 OUT2: 5000 6000 7000 8000\n")
        self.output(2, "2: OUT1: 900 1000 1100 1200\n" \
                           "2 OUT2: 9000 10000 11000 12000\n")

        self.execute(3, "0")
        self.execute(3, "1")
        self.execute(3, "2")

    def test_ireduce(self):
        output = "OUT1: 600 603 606 609\n" \
                 "OUT2: 6000000 6110601 6222408 6335427\n" \
                 "OUT1d: 0.6 0.603 0.606 0.609\n" \
                 "OUT2d: 0.006 0.0061106 0.00622241 0.00633543\n"
        self.program("ireduce")
        self.output(1, output)
        self.execute(3, "ok")

    def test_reduce1(self):
        output = "OUT1: 600 603 606 609\n" \
                 "OUT2: 6000000 6110601 6222408 6335427\n" \
                 "OUT3: 100 101 102 103\n" \
                 "OUT1d: 0.6 0.603 0.606 0.609\n" \
                 "OUT2d: 0.006 0.0061106 0.00622241 0.00633543\n" \
                 "OUT3d: 0.3 0.301 0.302 0.303\n"
        self.program("reduce")
        self.output(1, output)
        self.execute(3, "ok")

    def test_reduce2(self):
        output = "0 0 1 0\n" \
                 "1 1 1 0\n" \
                 "0 0 ff 0\n" \
                 "1 ff ffff 0\n"
        self.program("reduce2")
        self.output(1, output)
        self.execute(3)

    def test_allreduce(self):
        output = "OUT1: 600 603 606 609\n" \
                 "OUT2: 6000000 6110601 6222408 6335427\n" \
                 "OUT1d: 0.6 0.603 0.606 0.609\n" \
                 "OUT2d: 0.006 0.0061106 0.00622241 0.00633543\n"
        self.program("allreduce")

        self.output_default(output)
        self.execute(3, "allreduce")
        self.execute(3, "iallreduce")

    def test_reduce_scatter(self):
        self.program("reduce_scatter")
        self.output(0, "0 1000\n")
        self.output(1, "1 1004\n1 1008\n")
        self.output(2, "2 1012\n2 1016\n2 1020\n")
        self.output(3, "3 1024\n")
        self.execute(4)

    def test_reduce_scatter2(self):
        self.program("reduce_scatter2")
        self.execute(4, error="mpi/collective-mismatch/count")

    def test_loc(self):
        output = "int: (100, 1) (100, 1)\n" \
                 "int: (100, 3) (300, 30)\n" \
                 "int: (1, 3) (3, -5)\n" \
                 "double: (0.1, 1) (0.1, 1)\n" \
                 "double: (0.1, 3) (0.3, 30)\n" \
                 "double: (0.001, 3) (0.003, -5)\n"
        self.program("loc")
        self.output(1, output)
        self.execute(3, "ok")

    def test_scattergather(self):
        output = "OUT: 110 210 310 410 520 620 720 820 930 1030 1130 1230\n"
        self.program("scattergather")
        self.output(0, output)
        self.execute(3, "0")
        self.reset_output()
        self.output(1, output)
        self.execute(3, "1")
        self.reset_output()
        self.output(2, output)
        self.execute(3, "2")

    def test_scattergather_in_place(self):
        output = "OUT: 110 210 310 410 520 620 720 820 " \
                 "90300 100300 110300 120300 1340 1440 1540 1640\n"
        self.program("scattergather_in_place")
        self.output(2, output)
        self.execute(4, "2")

    def test_allgather(self):
        output = "OUT: 100 200 300 400 101 202 303 404 102 204 306 408\n"
        self.program("allgather")
        self.output_default(output)
        self.execute(3)

    def test_userop(self):
        self.program("userop")
        self.output_default("103 9\n")
        self.output(2, "103 9\nNC: 20 10\nNC: 30 10\nNC: 40 10\n")
        self.execute(4)

    def test_scan(self):
        self.program("scan")

        self.output(0, "OUT[0]: 10 10 10\n")
        self.execute(1)

        self.reset_output()
        self.output(0, "OUT[0]: 10 10 10\n")
        self.output(1, "OUT[1]: 15 5 50\n")
        self.output(2, "OUT[2]: 27 5 600\n")
        self.output(3, "OUT[3]: 40 5 7800\n")
        self.output(4, "OUT[4]: 40 0 0\n")
        self.execute(5)

    def test_in_place_err(self):
        self.program("in_place_err")
        self.execute(2, "scatter", error="mpi/collective-invalid-in-place")
        self.execute(2, "gather", error="mpi/collective-invalid-in-place")

    def test_invalid_order(self):
        self.program("invalid_order")
        self.execute(2, error="mpi/collective-mixing/type")

    def test_mixing(self):
        self.program("mixing")
        self.execute(2, error="mpi/collective-mixing/blocking-nonblocking")


if __name__ == "__main__":
    unittest.main()
