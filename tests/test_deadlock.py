
from utils import TestCase
import unittest

class DeadlockTests(TestCase):

    category = "deadlock"

    def test_simple_deadlock(self):
        self.program("simple")
        self.execute(2, send_protocol="eager")
        self.execute(2, send_protocol="rendezvous", error="mpi/deadlock")
        self.execute(2, send_protocol="full", error="mpi/deadlock")

    def test_send_protocol(self):
        self.program("deadlock1")
        self.execute(3, send_protocol="eager")
        self.execute(3, send_protocol="rendezvous")
        self.execute(3, send_protocol="3")
        self.execute(3, send_protocol="1M")
        self.execute(3, send_protocol="5", error="mpi/deadlock")
        self.execute(3, send_protocol="full", error="mpi/deadlock")

    def test_waitany(self):
        self.program("waitany")
        self.execute(3, send_protocol="eager")
        self.execute(3, send_protocol="full", error="mpi/deadlock")

    def test_waitany2(self):
        self.program("waitany2")
        self.execute(4, send_protocol="eager")
        self.execute(4, send_protocol="full", error="mpi/deadlock")

    def test_persistent(self):
        self.program("persistent")
        self.execute(3, send_protocol="eager")
        self.execute(3, send_protocol="full", error="mpi/deadlock")

    def test_barrier(self):
        self.program("barrier")
        self.execute(3, send_protocol="eager")
        self.execute(3, send_protocol="full", error="mpi/deadlock")

    def test_cc(self):
        self.program("cc")
        self.execute(7, send_protocol="eager")
        self.execute(7, send_protocol="full", error="mpi/deadlock")

    def test_cc2(self):
        self.program("cc2")
        self.execute(3, send_protocol="full")

    def test_prune(self):
        self.program("prune")
        self.execute(3, send_protocol="full")

    def test_cascade(self):
        self.program("cascade")
        self.execute(6, "0 0", send_protocol="full")
        self.execute(6, "1 0", send_protocol="full")
        self.execute(6, "0 1", send_protocol="full", error="mpi/deadlock")
        self.execute(6, "1 1", send_protocol="full", error="mpi/deadlock")

    def test_twocc(self):
        self.program("twocc")
        self.execute(3, send_protocol="eager")
        self.execute(3, send_protocol="full", error="mpi/deadlock")


if __name__ == "__main__":
    unittest.main()
