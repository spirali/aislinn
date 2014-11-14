
from utils import TestCase
import unittest

class ComplexTests(TestCase):

    category = "complex"

    def test_heatflow(self):
        files = ("heatflow.cpp", "compute.cpp")
        self.program("heatflow", files=files)

        self.execute(4, ("40", "40", "10", "10000"), stdout="")
        self.execute(8, ("40", "40", "10", "10000"), stdout="")

    def test_workers(self):
        files = ("workers.c",)
        self.program("workers", files=files)
        self.execute(3, ("4", "40"), stdout="")


if __name__ == "__main__":
    unittest.main()
