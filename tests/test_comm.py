
from utils import TestCase
import unittest

class CommTests(TestCase):

    category = "comm"

    def test_ranksize(self):
        self.program("ranksize")
        self.output(0, "0 3 0 1\n")
        self.output(1, "1 3 0 1\n")
        self.output(2, "2 3 0 1\n")
        self.execute(3)

    def test_selfsend(self):
        self.program("selfsend")
        self.output(1, "100 100 123\n")
        self.execute(2, send_protocol="randezvous")

    def test_selfgather(self):
        self.program("selfgather")
        self.output(1, "0\n101\n202\n303\n404\n")
        self.execute(3)

    def test_split(self):
        self.program("split")
        self.output(0, "0 1 2\n")
        self.output(1, "1 0 2\n")
        self.output(2, "2 1 2\n")
        self.output(3, "3 0 2\n")
        self.output(4, "4 0 1\n")
        self.output(5, "Ok\n")
        self.output(6, "Ok\n")
        self.execute(7)

    def test_split2(self):
        self.program("split2")
        self.output(1, "0 101 202\n1515\n")
        self.output(4, "303 404 505\n")
        self.execute(6)

    def test_dup(self):
        self.program("dup")
        self.output(0, "0 0 4 0 1\n")
        self.output(1, "1 1 4 0 1\n")
        self.output(2, "2 2 4 0 1\n")
        self.output(3, "3 3 4 0 1\n")
        self.execute(4)

    def test_free(self):
        self.program("free")
        self.output(0, "0 6 0 2\n")
        self.output(1, "1 6 1 2\n")
        self.output(2, "2 6 0 2\n")
        self.output(3, "3 6 1 2\n")
        self.output(4, "4 6 0 2\n")
        self.output(5, "5 6 1 2\n")
        self.execute(6)

    def test_free2(self):
        self.program("free2")
        self.execute(2, error="permanentcommfree")

    def test_compare(self):
        self.program("compare")
        self.execute(5)


if __name__ == "__main__":
    unittest.main()
