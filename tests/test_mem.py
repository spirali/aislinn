
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
        self.assertEquals(self.report.determinisic_nonfreed_memory, 100)
        self.execute(1, "100", heap_size="1M")
        self.assertEquals(self.report.determinisic_nonfreed_memory, 100)
        self.execute(1, "10000000", heap_size="1M", error="heaperror")
        self.execute(1, ("10000000",), heap_size="100M")
        self.assertEquals(self.report.determinisic_nonfreed_memory, 10000000)

    def test_leak(self):
        self.program("leak")
        self.execute(2, "100")
        self.execute(3, "100", error="not-freed-memory")

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

    def test_invaliddata(self):
        self.program("invaliddata")
        self.execute(1, "recv", error="invalid-recv-buffer")
        self.execute(1, "send", error="invalid-send-buffer")
        self.execute(1, "recv-lock", error="invalid-recv-buffer")
        self.execute(1, "send-lock", error="invalid-send-buffer")
        self.execute(1, "persistent-recv", error="invalid-recv-buffer")
        self.execute(1, "persistent-send", error="invalid-send-buffer")

    def test_lockedmem(self):
        self.program("lockedmem")
        self.execute(2, "1", error="invalidwrite-locked")
        self.execute(2, "2", error="invalidwrite-locked")

    def test_lockedmem_persistent(self):
        self.program("lockedmem-persistent")
        self.execute(2, "1")
        self.execute(2, "2", error="invalidwrite-locked")
        self.execute(2, "3")
        self.execute(2, "4", error="invalidwrite-locked")


if __name__ == "__main__":
    unittest.main()
