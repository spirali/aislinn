
from utils import TestCase
import unittest

class SendRecvTests(TestCase):

    category = "sendrecv"

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

    def test_status(self):
        output = "0 111\n2 333\n2 333\n0 111\n"
        self.program("status")
        self.execute(3, "wait", send_protocol="randezvous", stdout=output)
        self.no_errors()
        self.execute(3, "waitall", send_protocol="randezvous", stdout=output)
        self.no_errors()
        self.execute(3, "recv", send_protocol="randezvous", stdout=output)
        self.no_errors()

    def test_tag(self):
        self.program("tag")
        self.execute(2, "10 20", stdout="100 200\n")
        self.no_errors()
        self.execute(2, "20 10", stdout="200 100\n")
        self.no_errors()
        self.execute(2, "MPI_ANY_TAG MPI_ANY_TAG", stdout="100 200\n")
        self.no_errors()
        self.execute(2, "20 MPI_ANY_TAG", stdout="200 100\n")
        self.no_errors()
        self.execute(2, "10 1", stdout="")
        self.single_error("deadlock")


if __name__ == "__main__":
    unittest.main()
