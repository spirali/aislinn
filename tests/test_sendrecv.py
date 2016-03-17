
from utils import TestCase
import unittest


class SendRecvTests(TestCase):

    category = "sendrecv"

    def test_send_and_receive(self):
        self.program("send_and_receive")
        self.output(0, "Send\n")
        self.output(1, "Receive\n")
        self.execute(2, "1 ssend")
        self.execute(2, "1 bsend")
        self.execute(2, "0 bsend", error="mpi/deadlock")
        self.execute(2, "1 rsend")

        self.execute(2, "1 send")
        self.execute(2, "0 send", error="mpi/deadlock")

        # When Rsend is fully implemented, this should cause an error
        # self.execute(2, "1 rsend-err")

    def test_isend_irecv(self):
        self.program("isir")

        self.output(0, "Send\n")
        self.output(1, "Receive\n")
        self.execute(2, "1 send")
        self.execute(2, "0 send", error="mpi/deadlock")
        self.execute(2, "1 ssend")
        self.execute(2, "1 bsend")
        self.execute(2, "0 bsend", error="mpi/deadlock")
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

    def test_ssend(self):
        self.program("ssend")
        self.output(2, "200\n100\n")
        self.execute(3, "ssend")
        self.output(2, "100\n200\n")
        self.output(2, "200\n100\n")
        self.execute(3, "bsend")
        self.execute(3, "waitall")

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
        self.execute(2, ("1", "0"), error="base/exitcode")
        self.check_error("exitcode", pid="0", exitcode="1")
        self.execute(2, ("0", "2"), error="base/exitcode")
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

    def test_waitall2(self):
        self.program("waitall2")
        self.execute(1)

    def test_waitsome(self):
        self.program("waitsome")
        for output in ['1\n0 10 0 10\n3\n',
                       '1\n1 30 2 30\n3\n',
                       '1\n3 11 0 11\n3\n',
                       '1\n3 31 2 31\n3\n',
                       '1\n4 11 0 11\n3\n',
                       '1\n4 31 2 31\n3\n',
                       '2\n0 10 0 10\n1 30 2 30\n2\n',
                       '2\n0 10 0 10\n3 11 0 11\n2\n',
                       '2\n0 10 0 10\n3 31 2 31\n2\n',
                       '2\n0 10 0 10\n4 11 0 11\n2\n',
                       '2\n0 10 0 10\n4 31 2 31\n2\n',
                       '2\n1 30 2 30\n3 11 0 11\n2\n',
                       '2\n1 30 2 30\n3 31 2 31\n2\n',
                       '2\n1 30 2 30\n4 11 0 11\n2\n',
                       '2\n1 30 2 30\n4 31 2 31\n2\n',
                       '2\n3 11 0 11\n4 31 2 31\n2\n',
                       '2\n3 31 2 31\n4 11 0 11\n2\n',
                       '3\n0 10 0 10\n1 30 2 30\n3 11 0 11\n1\n',
                       '3\n0 10 0 10\n1 30 2 30\n3 31 2 31\n1\n',
                       '3\n0 10 0 10\n1 30 2 30\n4 11 0 11\n1\n',
                       '3\n0 10 0 10\n1 30 2 30\n4 31 2 31\n1\n',
                       '3\n0 10 0 10\n3 11 0 11\n4 31 2 31\n1\n',
                       '3\n0 10 0 10\n3 31 2 31\n4 11 0 11\n1\n',
                       '3\n1 30 2 30\n3 11 0 11\n4 31 2 31\n1\n',
                       '3\n1 30 2 30\n3 31 2 31\n4 11 0 11\n1\n',
                       '4\n0 10 0 10\n1 30 2 30\n3 11 0 11\n4 31 2 31\n0\n',
                       '4\n0 10 0 10\n1 30 2 30\n3 31 2 31\n4 11 0 11\n0\n']:
            self.output(1, output)
        self.execute(3)

    def test_waitsome2(self):
        self.program("waitsome2")
        self.execute(2)

    def test_waitsome3(self):
        self.program("waitsome3")
        self.execute(1, error="mem/invalid-write")

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

    def test_cross_send1(self):
        self.program("cross1")
        self.execute(2, send_protocol="eager")
        self.execute(2, send_protocol="rendezvous", error="mpi/deadlock")

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

        self.output(1, "First1 0 111\nFirst2 0 111 1\n"
                       "First3 0 111\nSecond 2 333\n")
        self.output(1, "First1 2 333\nFirst2 2 333 1\n"
                       "First3 2 333\nSecond 0 111\n")
        self.output(1, "First1 0 111\nFirst2 0 111 1\n"
                       "First3 2 333\nSecond 0 111\n")
        self.output(1, "First1 2 333\nFirst2 2 333 1\n"
                       "First3 0 111\nSecond 2 333\n")
        self.execute(3, "invalid-probe", send_protocol="rendezvous")
        self.execute(3, "invalid-iprobe", send_protocol="rendezvous")

    def test_probe(self):
        self.program("probe")
        self.output(1, "Found1\n")
        self.output(1, "Not found1\nFound2\n")
        self.output(1, "Not found1\nNot found2\nFound3\n")
        self.output(1, "Not found1\nNot found2\nNot found3\n")
        self.execute(2)

    def test_probe2(self):
        self.program("probe2")
        self.output(1, "12\n12\n11\n14\n14\n13\n")
        self.execute(2)

    def test_probe3(self):
        self.program("probe3")
        self.output(1, "0\n0\n2\n")
        self.output(1, "2\n2\n0\n")
        self.execute(3)

    def test_tag(self):
        self.program("tag")
        self.execute(2, "10 20", stdout="100 200\n")
        self.execute(2, "20 10", stdout="200 100\n")
        self.execute(2, "MPI_ANY_TAG MPI_ANY_TAG", stdout="100 200\n")
        self.execute(2, "20 MPI_ANY_TAG", stdout="200 100\n")
        self.execute(2, "10 1", stdout="", error="mpi/deadlock")

    def test_getcount(self):
        self.program("getcount")
        self.output(1, "369 123\n")
        self.execute(2)

    def test_partialrecv(self):
        self.program("partialrecv")
        self.execute(2, "2", stdout="2 0\n12\n13\n-1\n-1\n-1\n")
        self.execute(2, "4", stdout="4 0\n12\n13\n15\n21\n-1\n")
        self.execute(2, "6", error="mpi/message-truncated")

    def test_doublelock(self):
        self.program("doublelock")
        self.execute(2)
        self.execute(2, "write", error="mem/invalid-write")

if __name__ == "__main__":
    unittest.main()
