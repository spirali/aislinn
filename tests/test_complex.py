
from utils import TestCase
import unittest

class ComplexTests(TestCase):

    category = "complex"

    def test_heatflow(self):
        files = ("heatflow.cpp", "compute.cpp")
        self.program("heatflow", files=files)

        self.execute(4, ("40", "40", "10", "10000"), stdout="")
        self.execute(4, ("40", "40", "10", "10000"), stdout="", profile=True)
        self.assertTrue(len(self.report.get_icounts("process0")) == 1)
        self.assertTrue(len(self.report.get_icounts("process1")) == 1)
        self.assertTrue(len(self.report.get_icounts("process2")) == 1)
        self.assertTrue(len(self.report.get_icounts("process3")) == 1)
        self.assertTrue(len(self.report.get_icounts("global")) == 1)
        #self.execute(8, ("40", "40", "10", "10000"), stdout="")

    def test_workers(self):
        files = ("workers.c",)
        self.program("workers", files=files)
        self.execute(3, ("4", "40"), stdout="")
        self.execute(3, ("4", "40"), stdout="", send_protocol="eager", profile=True)
        self.assertTrue(len(self.report.get_icounts("process0")) == 1)
        self.assertTrue(len(self.report.get_icounts("process1")) > 10)
        self.assertTrue(len(self.report.get_icounts("process2")) > 10)
        self.assertTrue(len(self.report.get_icounts("global")) == 1)

if __name__ == "__main__":
    unittest.main()
