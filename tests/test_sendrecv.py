
from utils import TestCase
import unittest

class SendRecvTests(TestCase):

    category = "sendrecv"

    def test_send_and_receive(self):
        self.program("send_and_receive")
        self.execute(2, "1 ssend", stdout="Receive\nSend\n")
        self.execute(2, "1 bsend", stdout="Send\nReceive\n")
        self.execute(2, "0 bsend", error="deadlock")
        self.execute(2, "1 rsend", stdout="Send\nReceive\n")

        self.output(0, "Send\n")
        self.output(1, "Receive\n")
        self.execute(2, "1 send")
        self.execute(2, "0 send", error="deadlock")

        # When Rsend is fully implemented, this should cause an error
        # self.execute(2, "1 rsend-err")

    def test_isend_irecv(self):
        self.program("isir")

        self.output(0, "Send\n")
        self.output(1, "Receive\n")
        self.execute(2, "1 send")
        self.execute(2, "0 send", error="deadlock")
        self.execute(2, "1 ssend", stdout="Receive\nSend\n")
        self.execute(2, "1 bsend", stdout="Send\nReceive\n")
        self.execute(2, "0 bsend", error="deadlock")
        self.execute(2, "1 rsend")

        # When Rsend is fully implemented, this should cause an error
        # self.execute(2, "1 rsend-err")

    def test_sendrecv(self):
        self.program("sendrecv")
        self.output(0, "0 2 3\n")
        self.output(1, "1 0 1\n")
        self.output(2, "2 1 2\n")
        self.execute(3)
        self.output(0, "0 0 1\n")
        self.execute(1)

    def test_persistent(self):
        self.program("persistent")

        self.execute(2, "1 send1", stdout="101 202\n404 303\n")
        self.execute(2, "1 send2", stdout="101 202\n404 303\n")
        self.execute(2, "1 send3", stdout="101 202\n404 303\n")
        self.execute(2, "1 send4", stdout="101 202\n404 303\n")

    def test_testall_recv(self):
        self.program("testall_recv")
        self.output(0, "101 202 10 10\n")
        self.execute(2)

    def test_test_recv(self):
        self.program("test_recv")

        self.execute(2, ("0", "0"))
        self.execute(2, ("1", "0"), error="exitcode")
        self.check_error("exitcode", pid="0", exitcode="1")
        self.execute(2, ("0", "2"), error="exitcode")
        self.check_error("exitcode", pid="0", exitcode="2")

    def test_match1(self):
        self.program("match1")
        self.execute(2)

    def test_nullproc(self):
        self.program("nullproc")
        self.execute(2)

    def test_waitall(self):
        self.program("waitall")

        self.output(1, "101 201 103 203\n")
        self.output(1, "101 103 201 203\n")
        self.output(1, "101 103 203 201\n")
        self.output(1, "103 101 201 203\n")
        self.output(1, "103 101 203 201\n")
        self.output(1, "103 203 101 201\n")

        self.execute(3, ("a",), send_protocol="rendezvous")
        self.execute(3, ("a",))
        self.execute(3, ("b",), send_protocol="rendezvous")
        self.execute(3, ("b",))
        self.execute(3, ("c",), send_protocol="rendezvous")
        self.execute(3, ("c",))

    def test_waitany(self):
        self.program("waitany")

        self.output(1, "101 201 103 203\nSTATUS 0 5\n")
        self.output(1, "101 103 201 203\nSTATUS 0 5\n")
        self.output(1, "101 103 203 201\nSTATUS 0 5\n")
        self.output(1, "103 101 201 203\nSTATUS 0 5\n")
        self.output(1, "103 101 203 201\nSTATUS 0 5\n")
        self.output(1, "103 203 101 201\nSTATUS 0 5\n")


        self.output(1, "101 201 103 203\nSTATUS 2 5\n")
        self.output(1, "101 103 201 203\nSTATUS 2 5\n")
        self.output(1, "101 103 203 201\nSTATUS 2 5\n")
        self.output(1, "103 101 201 203\nSTATUS 2 5\n")
        self.output(1, "103 101 203 201\nSTATUS 2 5\n")
        self.output(1, "103 203 101 201\nSTATUS 2 5\n")

        self.execute(3, ("a",), send_protocol="rendezvous")
        self.execute(3, ("b",), send_protocol="rendezvous")

    def test_waitany2(self):
        self.program("waitany2")

        self.output(1, "101 201 103 203\nSTATUS 0 5\n")
        self.output(1, "101 201 103 203\nSTATUS 2 5\n")

        self.execute(3, ("a",), send_protocol="rendezvous")
        self.execute(3, ("b",), send_protocol="rendezvous")

    def test_waitany3(self):
        self.program("waitany3")
        self.execute(2)

    def test_send_protocol(self):
        self.program("deadlock1")
        self.execute(3, send_protocol="eager")
        self.execute(3, send_protocol="rendezvous")
        self.execute(3, send_protocol="3")
        self.execute(3, send_protocol="1M")
        self.execute(3, send_protocol="5", error="deadlock")
        self.execute(3, send_protocol="dynamic", error="deadlock")
        self.execute(3, send_protocol="full", error="deadlock")

    def test_cross_send1(self):
        self.program("cross1")
        self.execute(2, send_protocol="eager")
        self.execute(2, send_protocol="rendezvous", error="deadlock")

    def test_cross_send2(self):
        self.program("cross2")
        self.execute(2, send_protocol="eager")
        self.execute(2, send_protocol="rendezvous")
        self.execute(2)

    def test_types(self):
        self.program("types")
        self.execute(2, ("INT",))
        self.execute(2, ("LONG",))
        self.execute(2, ("FLOAT",))
        self.execute(2, ("DOUBLE",))

    def test_status(self):
        self.program("status")

        self.output(1, "0 111\n2 333\n")
        self.output(1, "2 333\n0 111\n")
        self.execute(3, "wait", send_protocol="rendezvous")
        self.execute(3, "waitall", send_protocol="rendezvous")
        self.execute(3, "recv", send_protocol="rendezvous")

        self.reset_output()
        self.output(1, "First1 0 111\nFirst2 0 111 1\n"
                           "First3 0 111\nSecond 2 333\n")
        self.output(1, "First1 2 333\nFirst2 2 333 1\n"
                           "First3 2 333\nSecond 0 111\n")
        self.execute(3, "probe", send_protocol="rendezvous")
        self.execute(3, "iprobe", send_protocol="rendezvous")

    def test_tag(self):
        self.program("tag")
        self.execute(2, "10 20", stdout="100 200\n")
        self.execute(2, "20 10", stdout="200 100\n")
        self.execute(2, "MPI_ANY_TAG MPI_ANY_TAG", stdout="100 200\n")
        self.execute(2, "20 MPI_ANY_TAG", stdout="200 100\n")
        self.execute(2, "10 1", stdout="", error="deadlock")

    def test_getcount(self):
        self.program("getcount")
        self.output(1, "369 123\n")
        self.execute(2)

    def test_partialrecv(self):
        self.program("partialrecv")
        self.execute(2, "2", stdout="2 0\n12\n13\n-1\n-1\n-1\n")
        self.execute(2, "4", stdout="4 0\n12\n13\n15\n21\n-1\n")
        self.execute(2, "6", error="message-truncated")


if __name__ == "__main__":
    unittest.main()
