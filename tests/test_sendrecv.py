
from utils import TestCase
import unittest

class SendRecvTests(TestCase):

    category = "sendrecv"

    def test_sendrecv(self):
        self.program("sendrecv")
        self.execute(2, "1 send")
        self.no_errors()

        self.execute(2, "0 send")
        self.single_error("deadlock")

        self.execute(2, "1 ssend", stdout="Receive\nSend\n")
        self.no_errors()

        self.execute(2, "1 bsend", stdout="Send\nReceive\n")
        self.no_errors()

        self.execute(2, "0 bsend")
        self.single_error("deadlock")

        self.execute(2, "1 rsend")
        self.no_errors()

        # When Rsend is fully implemented, this should cause an error
        # self.execute(2, "1 rsend-err")


    def test_isend_irecv(self):
        self.program("isir")

        self.execute(2, "1 send")
        self.no_errors()

        self.execute(2, "0 send")
        self.single_error("deadlock")

        self.execute(2, "1 ssend", stdout="Receive\nSend\n")
        self.no_errors()

        self.execute(2, "1 bsend", stdout="Send\nReceive\n")
        self.no_errors()

        self.execute(2, "0 bsend")
        self.single_error("deadlock")

        self.execute(2, "1 rsend")
        self.no_errors()

        # When Rsend is fully implemented, this should cause an error
        # self.execute(2, "1 rsend-err")


    def test_persistent(self):
        self.program("persistent")

        self.execute(2, "1 send1", stdout="101 202\n404 303\n")
        self.no_errors()

        self.execute(2, "1 send2", stdout="101 202\n404 303\n")
        self.no_errors()

        self.execute(2, "1 send3", stdout="101 202\n404 303\n")
        self.no_errors()

        self.execute(2, "1 send4", stdout="101 202\n404 303\n")
        self.no_errors()

    def test_testall_recv(self):
        self.program("testall_recv")

        self.execute(2, stdout=set(["101 202 10 10"]))
        self.no_errors()

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

    def test_nullproc(self):
        self.program("nullproc")
        self.execute(2, stdout="")
        self.no_errors()

    def test_waitall(self):
        result = set([
            "101 201 103 203",
            "101 103 201 203",
            "101 103 203 201",
            "103 101 201 203",
            "103 101 203 201",
            "103 203 101 201"
        ])

        self.program("waitall")
        self.execute(3, ("a",), stdout=result, send_protocol="randezvous")
        self.no_errors()

        self.execute(3, ("b",), stdout=result, send_protocol="randezvous")
        self.no_errors()

        self.execute(3, ("c",), stdout=result, send_protocol="randezvous")
        self.no_errors()

    def test_waitany(self):
        result = set([
            "101 201 103 203",
            "101 103 201 203",
            "101 103 203 201",
            "103 101 201 203",
            "103 101 203 201",
            "103 203 101 201",
            "STATUS 0 5",
            "STATUS 2 5",
        ])

        self.program("waitany")
        self.execute(3, ("a",), stdout=result, send_protocol="randezvous")
        self.no_errors()

        self.execute(3, ("b",), stdout=result, send_protocol="randezvous")
        self.no_errors()

    def test_waitany2(self):
        result = set([
            "101 201 103 203",
            "STATUS 0 5",
            "STATUS 2 5",
        ])

        self.program("waitany2")
        self.execute(3, ("a",), stdout=result, send_protocol="randezvous")
        self.no_errors()

        self.execute(3, ("b",), stdout=result, send_protocol="randezvous")
        self.no_errors()

    def test_waitany3(self):
        self.program("waitany3")
        self.execute(2)
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
        output2 = ("First1 0 111\n"
                   "First2 0 111 1\n"
                   "First3 0 111\n"
                   "Second 2 333\n"
                   "First1 2 333\n"
                   "First2 2 333 1\n"
                   "First3 2 333\n"
                   "Second 0 111\n")

        self.program("status")
        self.execute(3, "wait", send_protocol="randezvous", stdout=output)
        self.no_errors()
        self.execute(3, "waitall", send_protocol="randezvous", stdout=output)
        self.no_errors()
        self.execute(3, "recv", send_protocol="randezvous", stdout=output)
        self.no_errors()
        self.execute(3, "probe", send_protocol="randezvous", stdout=output2)
        self.no_errors()
        self.execute(3, "iprobe", send_protocol="randezvous", stdout=output2)
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

    def test_getcount(self):
        self.program("getcount")
        self.execute(2, stdout=set(["369 123"]))
        self.no_errors()

    def test_partialrecv(self):
        self.program("partialrecv")
        self.execute(2, "2", stdout="2 0\n12\n13\n-1\n-1\n-1\n")
        self.no_errors()
        self.execute(2, "4", stdout="4 0\n12\n13\n15\n21\n-1\n")
        self.no_errors()
        self.execute(2, "6")
        self.single_error("message-truncated")


if __name__ == "__main__":
    unittest.main()
