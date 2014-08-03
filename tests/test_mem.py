
from utils import TestCase
import unittest

class CommTests(TestCase):

    category = "mem"

    def test_heapwrite(self):
        self.program("heapwrite")

        self.execute(1, ("1",))
        self.single_error("invalidwrite")

if __name__ == "__main__":
    unittest.main()
