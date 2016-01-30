
from utils import TestCase
import unittest
import os
import subprocess


class VgIoTests(TestCase):

    category = "vgtool"

    def test_syscall(self):
        self.program("syscall")
        c = self.controller()
        c.stdout_file = open(os.devnull, "rb")
        c.start_and_connect()
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

    def test_syscall2(self):
        self.program("syscall")
        c = self.controller()
        c.stdout_file = subprocess.PIPE
        c.start_and_connect()
        c.set_capture_syscall("write", True)
        syscall = c.run_process().split()
        assert syscall[0] == "SYSCALL"
        assert syscall[1] == "write"
        assert syscall[4] == "9"
        length = syscall[4]
        c.run_drop_syscall(length)
        self.assertEquals(c.run_process(), "CALL Second")
        self.assertEquals(c.process.stdout.readline(), "Hello 2!\n")

    def test_printf(self):
        self.program("printf")
        c = self.controller(verbose=0)
        c.start_and_connect()
        c.set_capture_syscall("write", True)
        state1 = c.save_state()
        syscall = c.run_process().split()
        assert syscall[0] == "SYSCALL"
        assert syscall[1] == "write"
        assert syscall[4] == "9"
        length = syscall[4]
        c.run_drop_syscall(length)
        hash2 = c.hash_state()
        state2 = c.save_state()
        c.run_process()
        c.restore_state(state2)
        assert hash2 == c.hash_state()
        c.run_process()
        c.restore_state(state1)
        c.run_process()

    def test_open_write(self):
        self.program("openwrite")
        c = self.controller()
        syscalls = ("write", "open", "close")
        syscall = c.start_and_connect(capture_syscalls=syscalls).split()

        while True:
            assert syscall[0] == "SYSCALL"
            assert syscall[1] in ("open", "close")
            if syscall[1] == "open":
                filename = c.read_string(syscall[2])
                if filename == "data":
                    break
            syscall = c.run_process().split()
        syscall = c.run_drop_syscall(101).split()
        assert syscall[:3] == ["SYSCALL", "write", "101"]
        syscall = c.run_drop_syscall(syscall[4]).split()
        assert syscall == ["SYSCALL", "close", "101"]
        syscall = c.run_drop_syscall(0).split()
        assert syscall == ["EXIT", "0"]

    def test_open_read(self):
        self.program("openread")
        c = self.controller()
        syscalls = ("read", "open", "close")
        syscall = c.start_and_connect(capture_syscalls=syscalls).split()

        while True:
            assert syscall[0] == "SYSCALL"
            assert syscall[1] in ("open", "close", "read")
            if syscall[1] == "open":
                filename = c.read_string(syscall[2])
                if filename == "data":
                    break
            syscall = c.run_process().split()
        syscall = c.run_drop_syscall(101).split()
        assert syscall[:3] == ["SYSCALL", "read", "101"]
        file_content = "10 12\nxxabc\nfff"
        c.write_data(syscall[3], file_content)
        syscall = c.run_drop_syscall(len(file_content)).split()
        assert syscall[:3] == ["SYSCALL", "close", "101"]
        syscall = c.run_drop_syscall(0).split()
        assert syscall[:4] == ["CALL", "first", "10", "12"]
        assert c.read_string(syscall[4]) == "xxabc"


if __name__ == "__main__":
    unittest.main()
