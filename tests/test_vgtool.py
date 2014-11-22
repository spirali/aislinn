
from utils import TestCase
import unittest
import base.controller
import os
import subprocess

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
        c.kill()

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
        c.kill()

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
        c.kill()

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
        c.kill()

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
        c.kill()

    def test_syscall(self):
        self.program("syscall")
        c = self.controller()
        c.stdout_arg = open(os.devnull, "rb")
        c.start()
        s = c.save_state()

        self.assertEquals(c.run_process(), "CALL Second")
        c.restore_state(s)
        c.set_capture_syscall("write", True)
        action, syscall, fd, data_ptr, size = c.run_process().split()
        self.assertEquals(action, "SYSCALL")
        self.assertEquals(syscall, "write")
        self.assertEquals(fd, "1")
        self.assertEquals(c.read_mem(data_ptr, size), "Hello 1!\n")
        action, syscall, fd, data_ptr, size = c.run_process().split()
        self.assertEquals(action, "SYSCALL")
        self.assertEquals(syscall, "write")
        self.assertEquals(fd, "1")
        self.assertEquals(c.read_mem(data_ptr, size), "Hello 2!\n")
        self.assertEquals(c.run_process(), "CALL Second")

        c.restore_state(s)
        c.set_capture_syscall("write", False)
        self.assertEquals(c.run_process(), "CALL Second")

        c.kill()

    def test_syscall2(self):
        self.program("syscall")
        c = self.controller()
        c.stdout_arg = subprocess.PIPE
        c.start()
        c.set_capture_syscall("write", True)
        c.run_process()
        c.run_drop_syscall()
        self.assertEquals(c.run_process(), "CALL Second")
        self.assertEquals(c.process.stdout.readline(), "Hello 2!\n")
        c.kill()

    def test_access(self):
        INT_SIZE = 4
        self.program("access")

        c = self.controller(("10", "9"))
        ptr = self.get_call_1(c.start(), "init")
        self.assertEquals("Ok", c.check_is_writable(ptr, 10 * INT_SIZE))
        self.assertEquals(ptr + 10 * INT_SIZE, int(c.check_is_writable(ptr, 11 * INT_SIZE)))
        self.assertEquals("Ok", c.check_is_readable(ptr, 10 * INT_SIZE))
        self.assertEquals(ptr + 10 * INT_SIZE, int(c.check_is_readable(ptr, 11 * INT_SIZE)))
        self.assertEquals("EXIT 0", c.run_process())

        c = self.controller(("9", "10"))
        c.start()
        self.assertTrue(c.run_process().startswith("REPORT invalidwrite "))

        c = self.controller(("10", "9"))
        ptr = self.get_call_1(c.start(), "init")
        p2 = ptr + 6 * INT_SIZE
        c.lock_memory(p2, 4 * INT_SIZE)
        self.assertEquals("Ok", c.check_is_writable(ptr, INT_SIZE))
        self.assertEquals("Ok", c.check_is_readable(ptr, INT_SIZE))
        self.assertEquals(p2, int(c.check_is_writable(p2, INT_SIZE)))
        self.assertEquals("Ok", c.check_is_readable(p2, INT_SIZE))
        c.unlock_memory(p2, 4 * INT_SIZE)
        self.assertEquals("Ok", c.check_is_writable(p2, INT_SIZE))
        self.assertEquals("Ok", c.check_is_readable(p2, INT_SIZE))
        self.assertEquals("EXIT 0", c.run_process())

        c = self.controller(("10", "9"))
        ptr = self.get_call_1(c.start(), "init")
        c.lock_memory(ptr, 10 * INT_SIZE)
        self.assertEquals(int(ptr), int(c.check_is_writable(ptr, 11 * INT_SIZE)))
        self.assertEquals("Ok", c.check_is_readable(ptr, 10 * INT_SIZE))
        self.assertTrue(
                c.run_process().startswith("REPORT invalidwrite-locked"))

        s = 1000000 * INT_SIZE # 1M integers
        c = self.controller((str(s), "9"))
        ptr = self.get_call_1(c.start(), "init")
        self.assertEquals("Ok", c.check_is_writable(ptr, s))
        self.assertEquals("Ok", c.check_is_readable(ptr, s))
        p2 = ptr + 500000 * INT_SIZE
        c.lock_memory(p2, 1)
        self.assertEquals(p2, int(c.check_is_writable(ptr, s)))
        self.assertEquals("Ok", c.check_is_readable(ptr, s))
        c.unlock_memory(p2, 1)
        self.assertEquals("Ok", c.check_is_writable(ptr, s))
        self.assertEquals("Ok", c.check_is_readable(ptr, s))
        self.assertEquals("EXIT 0", c.run_process())

    def get_call_1(self, line, name):
        args = line.split()
        self.assertEquals(len(args), 3, "Invalid output:" + line)
        self.assertEquals(args[0], "CALL")
        self.assertEquals(args[1], name)
        return int(args[2])



if __name__ == "__main__":
    unittest.main()
