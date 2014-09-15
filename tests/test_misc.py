
from utils import TestCase
import unittest

class MiscTests(TestCase):

    category = "misc"

    def test_dimcreate(self):
        output = "3 2\n3 10\n2 512\n7 1\n10 20\n1 1\n12 11 6\n"
        self.program("dimcreate")
        self.execute(1, stdout=output)
        self.no_errors()

if __name__ == "__main__":
    unittest.main()
