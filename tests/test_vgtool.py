
from utils import TestCase
import unittest
import os
import subprocess


class VgToolTests(TestCase):

    category = "vgtool"

    def test_simple(self):
        self.program("simple")
        c = self.controller(verbose=0)
        self.assertEquals(c.start_and_connect(), "CALL Hello 1")
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
        call, name, arg = c.start_and_connect().split()
        h1 = c.hash_state()
        c.write_int(arg, 211)
        h2 = c.hash_state()
        self.assertNotEquals(h1, h2)
        c.write_int(arg, 210)
        h3 = c.hash_state()
        self.assertEquals(h1, h3)

    def test_global(self):
        self.program("global")
        c = self.controller()
        call, name, arg = c.start_and_connect().split()
        h1 = c.hash_state()
        c.write_int(arg, 211)
        h2 = c.hash_state()
        self.assertNotEquals(h1, h2)
        c.write_int(arg, 210)
        h3 = c.hash_state()
        self.assertEquals(h1, h3)

    def test_restore_after_quit(self):
        self.program("simple")
        c = self.controller()
        self.assertEquals(c.start_and_connect(), "CALL Hello 1")
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
        call, name, fn_a, fn_b = c.start_and_connect().split()
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

    def test_access(self):
        INT_SIZE = 4
        self.program("access")

        c = self.controller(("10", "9"))
        ptr = self.get_call_1(c.start_and_connect(), "init")
        self.assertEquals("Ok", c.is_writable(ptr, 10 * INT_SIZE))
        self.assertEquals(
            ptr + 10 * INT_SIZE, int(c.is_writable(ptr, 11 * INT_SIZE)))
        self.assertEquals("Ok", c.is_readable(ptr, 10 * INT_SIZE))
        self.assertEquals(
            ptr + 10 * INT_SIZE, int(c.is_readable(ptr, 11 * INT_SIZE)))
        self.assertEquals("EXIT 0", c.run_process())

        c = self.controller(("9", "10"))
        c.start_and_connect()
        self.assertTrue(c.run_process().startswith("REPORT invalidwrite "))

        c = self.controller(("10", "9"))
        ptr = self.get_call_1(c.start_and_connect(), "init")
        p2 = ptr + 6 * INT_SIZE
        c.lock_memory(p2, 4 * INT_SIZE)
        self.assertEquals("Ok", c.is_writable(ptr, INT_SIZE))
        self.assertEquals("Ok", c.is_readable(ptr, INT_SIZE))
        self.assertEquals(p2, int(c.is_writable(p2, INT_SIZE)))
        self.assertEquals("Ok", c.is_readable(p2, INT_SIZE))
        c.unlock_memory(p2, 4 * INT_SIZE)
        self.assertEquals("Ok", c.is_writable(p2, INT_SIZE))
        self.assertEquals("Ok", c.is_readable(p2, INT_SIZE))
        self.assertEquals("EXIT 0", c.run_process())

        c = self.controller(("10", "9"))
        ptr = self.get_call_1(c.start_and_connect(), "init")
        c.lock_memory(ptr, 10 * INT_SIZE)
        self.assertEquals(int(ptr), int(c.is_writable(ptr, 11 * INT_SIZE)))
        self.assertEquals("Ok", c.is_readable(ptr, 10 * INT_SIZE))
        self.assertTrue(
            c.run_process().startswith("REPORT invalidwrite"))

        s = 1000000 * INT_SIZE  # 1M integers
        c = self.controller((str(s), "9"))
        ptr = self.get_call_1(c.start_and_connect(), "init")
        self.assertEquals("Ok", c.is_writable(ptr, s))
        self.assertEquals("Ok", c.is_readable(ptr, s))
        p2 = ptr + 500000 * INT_SIZE
        c.lock_memory(p2, 1)
        self.assertEquals(p2, int(c.is_writable(ptr, s)))
        self.assertEquals("Ok", c.is_readable(ptr, s))
        c.unlock_memory(p2, 1)
        self.assertEquals("Ok", c.is_writable(ptr, s))
        self.assertEquals("Ok", c.is_readable(ptr, s))
        self.assertEquals("EXIT 0", c.run_process())

    def get_call_1(self, line, name):
        args = line.split()
        self.assertEquals(len(args), 3, "Invalid output:" + line)
        self.assertEquals(args[0], "CALL")
        self.assertEquals(args[1], name)
        return int(args[2])

    def test_write_into_buffer(self):
        self.program("two_allocations")
        c = self.controller()
        mem1 = int(c.start_and_connect().split()[2])
        mem2 = int(c.run_process().split()[2])
        # buffer 500 - small buffer
        # buffer 600 - big buffer
        c.make_buffer(500, 10)
        c.make_buffer(600, 100000)
        data1 = "abc123"
        data2 = "abcABCwxyz" * 10000
        c.write_data_into_buffer(500, 2, data1)
        c.write_data_into_buffer(600, 0, data2)
        c.write_buffer(mem1, 500)
        c.write_buffer(mem2, 600)
        self.assertEquals(data1, c.read_mem(mem1 + 2, 6))
        self.assertEquals(data2, c.read_mem(mem2, 100000))
        self.assertEquals("EXIT 0", c.run_process())
        c.free_buffer(500)
        c.free_buffer(600)

    def test_lock_and_restore(self):
        self.program("two_allocations")
        c = self.controller()
        mem1 = int(c.start_and_connect().split()[2])
        c.write_int(mem1, 10)
        hash1 = c.hash_state()
        c.lock_memory(mem1, c.INT_SIZE)
        hash2 = c.hash_state()
        assert hash1 != hash2
        state2 = c.save_state()
        c.unlock_memory(mem1, c.INT_SIZE)
        c.write_int(mem1, 20)
        c.lock_memory(mem1, c.INT_SIZE)
        hash3 = c.hash_state()
        assert hash3 != hash1
        assert hash3 != hash2
        c.restore_state(state2)
        hash4 = c.hash_state()
        assert hash4 == hash2
        self.assertEquals(10, c.read_int(mem1))

    def test_bigalloc(self):
        self.program("bigalloc")
        c = self.controller()
        c.start_and_connect().split()[2]
        mem = int(c.run_process().split()[2])
        state1 = c.save_state()
        hash1 = c.hash_state()
        # Do not modifiy the first page -> write after first 64kb)
        for i in xrange(1000):
            c.write_int(mem + i * 10 * 1024 + 200000, 0xFF00FF00)
        state2 = c.save_state()
        hash2 = c.hash_state()
        assert hash1 != hash2
        c.restore_state(state1)
        assert hash1 == c.hash_state()
        c.run_process()
        hash3 = c.hash_state()
        assert hash3 != hash1
        assert hash3 != hash2
        c.restore_state(state2)
        c.run_process()
        assert hash3 == c.hash_state()
        c.run_process()

    def test_mmap(self):
        self.program("mmap")
        c = self.controller(verbose=0)
        c.start_and_connect()
        hash1 = c.hash_state()
        state1 = c.save_state()
        assert c.run_process() == "CALL Second"
        hash2 = c.hash_state()
        state2 = c.save_state()
        assert c.run_process() == "CALL Third"
        hash3 = c.hash_state()
        assert c.run_process() == "EXIT 0"
        hash4 = c.hash_state()

        c.restore_state(state2)
        assert c.hash_state() == hash2
        assert c.run_process() == "CALL Third"
        assert c.hash_state() == hash3

        c.restore_state(state2)
        c.restore_state(state1)
        assert c.hash_state() == hash1
        assert c.run_process() == "CALL Second"
        assert c.hash_state() == hash2

        assert c.run_process() == "CALL Third"
        assert c.run_process() == "EXIT 0"
        assert c.hash_state() == hash4

    def test_profile(self):
        def get_profile(value):
            data = value.split()
            self.assertEquals(data[0], "PROFILE")
            return map(int, data[1:])
        self.program("simple")
        c = self.controller(profile=True)
        i1 = get_profile(c.start_and_connect())
        self.assertEquals(c.receive_line(), "CALL Hello 1")
        i2 = get_profile(c.run_process())
        self.assertEquals(c.receive_line(), "CALL Hello 2")
        i3 = get_profile(c.run_process())
        self.assertEquals(c.receive_line(), "EXIT 0")
        assert i1[0] > i2[0] and i3[0] > i2[0]
        assert i1[1] == i2[1] == i3[1] == 0
        assert i1[2] == i2[2] == i3[2] == 0

    def test_string(self):
        self.program("string")
        c = self.controller()
        ptr1 = c.start_and_connect().split()[2]
        assert c.read_string(ptr1) == "This is\n my\n string!"

    def test_bigstack(self):
        size = 5 * 1024  # 500KiB
        self.program("bigstack")
        c = self.controller(verbose=0)
        c.start_and_connect()
        state1 = c.save_state()
        call, name, addr = c.run_process().split()
        state2 = c.save_state()
        c.run_process()
        state3 = c.save_state()
        c.run_process()
        c.hash_state()

        c.restore_state(state1)
        c.restore_state(state2)
        v = c.read_mem(addr, size)
        assert map(ord, v) == [0xaa] * size
        c.restore_state(state3)
        v = c.read_mem(addr, size)
        assert map(ord, v) == [0xbb] * size

    def test_stack_pollution(self):
        self.program("stackpollution")
        c = self.controller()
        c.start_and_connect()
        s1 = c.save_state()
        c.run_process()  # call g
        hash1 = c.hash_state()
        c.run_process()  # finish
        c.restore_state(s1)
        c.run_process()  # call g

        hash2 = c.hash_state()

        assert hash1 == hash2


if __name__ == "__main__":
    unittest.main()
