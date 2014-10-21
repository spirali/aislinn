
from utils import TestCase
import unittest

class MemTests(TestCase):

    category = "mem"

    def test_heapwrite(self):
        self.program("heapwrite")

        self.execute(1, ("1",))
        self.single_error("invalidwrite")

    def test_mem(self):
        self.program("memalign")
        self.execute(1, stdout="")
        self.no_errors()

if __name__ == "__main__":
    unittest.main()
