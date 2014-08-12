
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

if __name__ == "__main__":
    unittest.main()
