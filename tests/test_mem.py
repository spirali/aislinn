
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

    def test_heapsize(self):
        self.program("malloc")

        self.execute(1, ("100",))
        self.no_errors()


        self.execute(1, ("100",), heapsize="1M")
        self.no_errors()

        self.execute(1,
                     ("10000000",),
                     heapsize="1M")
        self.single_error("heaperror")

        self.execute(1, ("10000000",), heapsize="100M")
        self.no_errors()

    def test_malloc_free(self):
        self.program("mallocfree")
        self.execute(1)
        self.no_errors()


if __name__ == "__main__":
    unittest.main()
