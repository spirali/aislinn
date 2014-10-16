
from utils import TestCase
import unittest

class VgToolTests(TestCase):

    category = "vgtool"

    def test_simple(self):
        self.program("simple")
        c = self.controller()
        #c.valgrind_args = ("--verbose=1",)
        self.assertEquals(c.start(), "CALL Hello 1")
        h = c.hash_state()
        s = c.save_state()
        h2 = c.hash_state()
        self.assertEquals(h, h2)
        c.restore_state(s)
        h3 = c.hash_state()
        self.assertEquals(h, h3)

        self.assertEquals(c.run_process(), "CALL Hello 2")
        h4 = c.hash_state()
        s2 = c.save_state()
        self.assertNotEquals(h, h4)
        self.assertEquals(h4, c.hash_state())

        self.assertEquals(c.run_process(), "EXIT 0")
        s3 = c.save_state()
        h5 = c.hash_state()
        self.assertNotEquals(h, h5)
        self.assertNotEquals(h4, h5)

        c.restore_state(s)
        self.assertEquals(h, c.hash_state())

        c.restore_state(s2)
        self.assertEquals(h4, c.hash_state())

        c.restore_state(s3)
        self.assertEquals(h5, c.hash_state())

        c.free_state(s)
        c.free_state(s2)
        c.free_state(s3)

        stats = c.get_stats()
        # All pages are active
        self.assertEquals(stats["pages"], stats["active-pages"])

    def test_local(self):
        self.program("local")
        c = self.controller(verbose=False)
        call, name, arg = c.start().split()
        h1 = c.hash_state()
        c.write_int(arg, 211);
        h2 = c.hash_state()
        self.assertNotEquals(h1, h2)
        c.write_int(arg, 210);
        h3 = c.hash_state()
        self.assertEquals(h1, h3)

    def test_global(self):
        self.program("global")
        c = self.controller()
        call, name, arg = c.start().split()
        h1 = c.hash_state()
        c.write_int(arg, 211);
        h2 = c.hash_state()
        self.assertNotEquals(h1, h2)
        c.write_int(arg, 210);
        h3 = c.hash_state()
        self.assertEquals(h1, h3)

    def test_restore_after_quit(self):
        self.program("simple")
        c = self.controller()
        self.assertEquals(c.start(), "CALL Hello 1")
        s = c.save_state()
        h1 = c.hash_state()
        self.assertEquals(c.run_process(), "CALL Hello 2")
        h2 = c.hash_state()
        self.assertEquals(c.run_process(), "EXIT 0")
        h3 = c.hash_state()

        c.restore_state(s)
        g1 = c.hash_state()
        self.assertEquals(c.run_process(), "CALL Hello 2")
        g2 = c.hash_state()
        self.assertEquals(c.run_process(), "EXIT 0")
        g3 = c.hash_state()

        self.assertEquals(h1, g1)
        self.assertEquals(h2, g2)
        self.assertEquals(h3, g3)

        self.assertNotEquals(h1, h2)
        self.assertNotEquals(h2, h3)
        self.assertNotEquals(h2, h3)

    def test_function_call(self):
        self.program("function")
        c = self.controller()
        call, name, fn_a, fn_b = c.start().split()
        self.assertEquals(call, "CALL")
        self.assertEquals(name, "INIT")
        s = c.save_state()
        self.assertEquals(c.run_process(), "CALL RUN")
        self.assertEquals(c.run_function(fn_a, 0, 10), "CALL A 10")
        self.assertEquals(c.run_function(fn_a, 0, 20), "CALL A 20")
        self.assertEquals(c.run_process(), "FUNCTION_FINISH")
        self.assertEquals(c.run_process(), "FUNCTION_FINISH")
        self.assertEquals(c.run_function(fn_b, 0, 30), "CALL B 30")
        self.assertEquals(c.run_process(), "FUNCTION_FINISH")
        self.assertEquals(c.run_process(), "EXIT 0")
        c.restore_state(s)
        self.assertEquals(c.run_function(fn_b, 0, 40), "CALL B 40")
        self.assertEquals(c.run_process(), "FUNCTION_FINISH")

if __name__ == "__main__":
    unittest.main()
