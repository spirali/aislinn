
from utils import TestCase
import unittest

class ComplexTests(TestCase):

    category = "complex"

    def test_heatflow(self):
        files = ("heatflow.cpp", "compute.cpp")
        self.program("heatflow", files=files)

        self.execute(4, ("40", "40", "10", "10000"))
        self.no_errors()

        self.execute(8, ("40", "40", "10", "10000"))
        self.no_errors()

    def test_workers(self):
        files = ("workers.c",)
        self.program("workers", files=files)

        self.execute(3, ("4", "40"))
        self.no_errors()


if __name__ == "__main__":
    unittest.main()
