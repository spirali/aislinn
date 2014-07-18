
from utils import TestCase
import unittest

class CommTests(TestCase):

    category = "comm"

    def test_sendrecv(self):
        self.program("sendrecv")

        self.execute(2, ("1",))
        self.no_errors()

        self.execute(2, ("0",))
        self.single_error("deadlock")

    def test_isend_irecv(self):
        self.program("isir")

        self.execute(2, ("1",))
        self.no_errors()

        self.execute(2, ("0",))
        self.single_error("deadlock")

    def test_test_recv(self):
        self.program("test_recv")

        self.execute(2, ("0", "0"))
        self.no_errors()

        self.execute(2, ("1", "0"))
        self.exit_code_error(0, 1)

        self.execute(2, ("0", "2"))
        self.exit_code_error(0, 2)

    def test_match1(self):
        self.program("match1")
        self.execute(2)
        self.no_errors()

    def test_waitall(self):
        result = [
            "101 201 103 203",
            "101 103 201 203",
            "101 103 203 201",
            "103 101 201 203",
            "103 101 203 201",
            "103 203 101 201"
        ]
        result.sort()

        def check_output(stdout):
            lines = stdout.rstrip().split("\n")
            lines.sort()
            self.assertEquals(result, lines)

        self.program("waitall")
        self.execute(3, ("a",), stdout=check_output, send_protocol="randezvous")
        self.no_errors()

        self.execute(3, ("b",), stdout=check_output, send_protocol="randezvous")
        self.no_errors()

        self.execute(3, ("c",), stdout=check_output, send_protocol="randezvous")
        self.no_errors()

    def test_send_protocol(self):
        self.program("deadlock1")
        self.execute(3, send_protocol="eager")
        self.no_errors()
        self.execute(3, send_protocol="randezvous")
        self.no_errors()
        self.execute(3, send_protocol="3")
        self.no_errors()
        self.execute(3, send_protocol="1M")
        self.no_errors()
        self.execute(3, send_protocol="5")
        self.single_error("deadlock")
        self.execute(3, send_protocol="dynamic")
        self.single_error("deadlock")
        self.execute(3, send_protocol="full")
        self.single_error("deadlock")

    def test_cross_send1(self):
        self.program("cross1")
        self.execute(2, send_protocol="eager")
        self.no_errors()
        self.execute(2, send_protocol="randezvous")
        self.single_error("deadlock")

    def test_cross_send2(self):
        self.program("cross2")
        self.execute(2, send_protocol="eager")
        self.no_errors()
        self.execute(2, send_protocol="randezvous")
        self.no_errors()
        self.execute(2)
        self.no_errors()

    def test_types(self):
        self.program("types")
        self.execute(2, ("INT",))
        self.no_errors()

        self.execute(2, ("LONG",))
        self.no_errors()

        self.execute(2, ("FLOAT",))
        self.no_errors()

        self.execute(2, ("DOUBLE",))
        self.no_errors()


if __name__ == "__main__":
    unittest.main()
