
from utils import TestCase, make_set
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
        self.execute(6, stdout=None)
        self.no_errors()

    def test_dup(self):
        output = make_set("0 0 4 0 1\n1 1 4 0 1\n2 2 4 0 1\n3 3 4 0 1")
        self.program("dup")
        self.execute(4, stdout=output)
        self.no_errors()

    def test_free(self):
        output = "0 6 0 2\n" \
                 "1 6 1 2\n" \
                 "2 6 0 2\n" \
                 "3 6 1 2\n" \
                 "4 6 0 2\n" \
                 "5 6 1 2"

        self.program("free")
        self.execute(6, stdout=set(output.split("\n")))
        self.no_errors()

    def test_free2(self):
        self.program("free2")
        self.execute(2, stdout="")
        self.single_error("permanentcommfree")

    def test_compare(self):
        self.program("compare")
        self.execute(5, stdout="")
        self.no_errors()


if __name__ == "__main__":
    unittest.main()
