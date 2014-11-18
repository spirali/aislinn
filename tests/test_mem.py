
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
        self.execute(1, "100", heap_size="1M")
        self.execute(1, "10000000", heap_size="1M", error="heaperror")
        self.execute(1, ("10000000",), heap_size="100M")

    def test_malloc_free(self):
        self.program("mallocfree")
        self.execute(1)

    def test_invalid_mem(self):
        self.program("invalidmem")
        self.execute(1, "noinit", error="invalidwrite")
        self.execute(1, error="invalidwrite")

    def test_redzones(self):
        def check_stdout(data, limit):
            for value in map(int, data.splitlines()):
                self.assertTrue(
                        value >= limit,
                        "The gap between two allocation is no sufficient")
            return True
        self.program("redzones")
        self.execute(1, stdout=lambda data: check_stdout(data, 16), redzone_size=16)
        self.execute(1, stdout=lambda data: check_stdout(data, 100), redzone_size=100)
        self.execute(1, stdout=lambda data: check_stdout(data, 6000), redzone_size=6000)

if __name__ == "__main__":
    unittest.main()
