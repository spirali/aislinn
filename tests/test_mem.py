
from utils import TestCase
import unittest

class MemTests(TestCase):

    category = "mem"

    def test_heapwrite(self):
        self.program("heapwrite")
        self.execute(1, "1", error="invalidwrite")

    def test_mem(self):
        self.program("memalign")
        self.execute(1)

    def test_heapsize(self):
        self.program("malloc")

        self.execute(1, "100")
        self.execute(1, "100", heapsize="1M")
        self.execute(1, "10000000", heapsize="1M", error="heaperror")
        self.execute(1, ("10000000",), heapsize="100M")

    def test_malloc_free(self):
        self.program("mallocfree")
        self.execute(1)

    def test_invalid_mem(self):
        self.program("invalidmem")
        self.execute(1, "noinit", error="invalidwrite")
        self.execute(1, error="invalidwrite")


if __name__ == "__main__":
    unittest.main()
