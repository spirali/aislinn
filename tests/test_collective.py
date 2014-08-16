
from utils import TestCase
import unittest

class CollectiveTests(TestCase):

    category = "collective"

    def test_invalid(self):
        self.program("invalid")

        args = [ "gatherv_root",
                 "gatherv_sendcount" ]

        for arg in args:
            self.execute(2, (arg,))
            self.single_error("invalidarg", rank=0)

    def test_ibarrier(self):
        self.program("ibarrier")

        def check_output1(output):
            self.assertEquals(set(output.strip().split("\n")),
                              set(["a = 0; b = 200", "a = 200; b = 0"]))
        def check_output2(output):
            self.assertEquals(set(output.strip().split("\n")), set(["a = 0; b = 200"]))

        self.execute(3, "a", stdout=check_output1)
        self.no_errors()
        self.execute(3, "b", stdout=check_output2)
        self.no_errors()

    def test_gatherv(self):
        output1 = "OUT1: 100 101\n" \
                  "OUT2: 100 101\n"
        output3 = "OUT1: 100 101 102 103 104 105 200 201 202 203 204 300 301 302 303\n"\
                  "OUT2: 100 101 102 103 104 105 200 201 202 203 204 300 301 302 303\n"
        self.program("gatherv")

        self.execute(1, "waitall", stdout=output1)
        self.no_errors()
        self.execute(3, "waitall", stdout=output3)
        self.no_errors()

        self.execute(1, "wait", stdout=output1)
        self.no_errors()
        self.execute(3, "wait", stdout=output3)
        self.no_errors()

        self.execute(3, "mismatch")
        self.single_error("rootmismatch")

    def test_igather(self):
        output = "OUT1: 100 101 102 103 200 201 202 203 300 301 302 303\n" \
                 "OUT2: 1000 1001 1002 1003 2000 2001 2002 2003 3000 3001 3002 3003\n"
        self.program("igather")
        self.execute(3, "0", stdout=output)
        self.no_errors()
        self.execute(3, "1", stdout=output)
        self.no_errors()
        self.execute(3, "2", stdout=output)
        self.no_errors()


if __name__ == "__main__":
    unittest.main()
