from utils import TestCase
import unittest
import os
import subprocess
from base.controller import make_interconnection


class VgToolTests(TestCase):

    category = "vgtool"

    def test_pushpull(self):
        self.program("string")
        c = self.controller(verbose=0)
        c.start_and_connect()
        c.client_malloc(1024 * 1024 * 5)
        h1 = c.hash_state()
        state_id = c.save_state()
        d = self.controller()
        d.start_and_connect()
        sockets = make_interconnection((c, d))

        c_to_d = sockets[0][1]
        d_to_c = sockets[1][0]

        c.push_state(c_to_d, state_id)
        s1 = d.pull_state(d_to_c)
        d.restore_state(s1)
        h2 = d.hash_state()

        d.push_state(d_to_c, s1)
        s2 = c.pull_state(c_to_d)
        c.restore_state(s2)
        h3 = c.hash_state()

        s3 = c.save_state()

        c.push_state(c_to_d, s3)
        s4 = d.pull_state(d_to_c)
        d.restore_state(s4)
        h4 = d.hash_state()

        c.restore_state(state_id)
        h5 = c.hash_state()

        c.restore_state(s2)
        h6 = c.hash_state()

        assert h1 == h2
        assert h2 == h3
        assert h3 == h4
        assert h4 == h5
        assert h5 == h6

    def test_printf_pushpull(self):
        self.program("printf")
        c = self.controller(verbose=1)
        c.start_and_connect()
        c.run_process()
        state_id = c.save_state()
        h1 = c.hash_state()

        d = self.controller(verbose=1)
        d.start_and_connect()
        sockets = make_interconnection((c, d))

        c_to_d = sockets[0][1]
        d_to_c = sockets[1][0]

        c.push_state(c_to_d, state_id)
        s1 = d.pull_state(d_to_c)
        d.restore_state(s1)
        h2 = d.hash_state()

        assert h1 == h2

        c.run_process()
        d.run_process()
        assert c.hash_state() == d.hash_state()

    def test_bigstack_pushpull(self):
        self.program("bigstack2")
        c = self.controller()
        c.start_and_connect()
        state_id = c.save_state()
        h1 = c.hash_state()

        d = self.controller()
        d.start_and_connect()
        sockets = make_interconnection((c, d))

        c_to_d = sockets[0][1]
        d_to_c = sockets[1][0]

        c.push_state(c_to_d, state_id)
        s1 = d.pull_state(d_to_c)
        d.restore_state(s1)
        h2 = d.hash_state()

        assert h1 == h2

    def test_connect(self):
        self.program("string")
        c = self.controller()
        c.start_and_connect()
        port = c.interconn_listen()

        d = self.controller()
        d.start_and_connect()
        d.interconn_connect("127.0.0.1:" + str(port))

        c_sock = c.interconn_listen_finish()
        d_sock = d.interconn_connect_finish()
        assert c_sock > 0
        assert d_sock > 0

    def test_interconnect(self):
        self.program("string")
        controllers = [ self.controller() for c in xrange(6) ]
        for c in controllers:
            c.start_and_connect()
        sockets = make_interconnection(controllers)

        assert len(sockets) == len(controllers)
        for i, ss in enumerate(sockets):
            assert len(ss) == len(controllers)
            for j, s in enumerate(ss):
                if i == j:
                    assert s is None
                else:
                    assert s > 0

if __name__ == "__main__":
    unittest.main()
