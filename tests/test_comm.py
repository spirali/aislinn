
from utils import TestCase
import unittest

class CommTests(TestCase):

    category = "comm"

    def test_ranksize(self):
        output = "0 3 0 1\n1 3 0 1\n2 3 0 1\n"

        self.program("ranksize")
        self.execute(3, stdout=output)
        self.no_errors()

    def test_selfsend(self):
        output = "100 100 123\n"

        self.program("selfsend")
        self.execute(2, stdout=output, send_protocol="randezvous")
        self.no_errors()

    def test_selfgather(self):
        output = "0\n101\n202\n303\n404\n"

        self.program("selfgather")
        self.execute(3, stdout=output)
        self.no_errors()

    def test_split(self):
        output = "0 1 2\n1 0 2\n2 1 2\n3 0 2\n4 0 1\nOk\nOk\n"
        self.program("split")
        self.execute(7, stdout=output)
        self.no_errors()

    def test_split2(self):
        output = set(["0 101 202", "1515", "303 404 505"])
        self.program("split2")
        self.execute(6, stdout=output)
        self.no_errors()


if __name__ == "__main__":
    unittest.main()
