#
#    Copyright (C) 2014 Stanislav Bohm
#
#    This file is part of Aislinn.
#
#    Aislinn is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 of the License, or
#    (at your option) any later version.
#
#    Aislinn is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Aislinn.  If not, see <http://www.gnu.org/licenses/>.
#


from statespace import StateSpace
from node import Node
from arc import Arc
from stream import STREAM_STDOUT, StreamChunk

import pytest


def make_node(s, parent, name, events=None, streams=None):
    n = s.get_node_by_hash("#" + name + "#")
    if n is None:
        n = Node(name, "#" + name + "#")
        s.add_node(n)
    if parent:
        p = s.get_node_by_hash("#" + parent + "#")
        p.add_arc(Arc(n, events, streams))
        n.prev = p
    else:
        s.initial_node = n
    return n


def stdout(pid, data):
    return StreamChunk(STREAM_STDOUT, pid, data)


@pytest.fixture
def sspace_empty():
    """
        Statespace example
    """
    s = StateSpace()
    make_node(s, None, "init")
    return s


@pytest.fixture
def sspace_fork1():
    """
        Statespace example

        n1 --0a- n11
           \-0b- n12
    """
    s = StateSpace()
    make_node(s, None, "n1")
    make_node(s, "n1", "n11", None, [stdout(0, "a")])
    make_node(s, "n1", "n12", None, [stdout(0, "b")])
    return s


@pytest.fixture
def sspace_fork2():
    """
        Statespace example

        n1 --0aa- n11
           \-0aa- n12
    """
    s = StateSpace()
    make_node(s, None, "n1")
    make_node(s, "n1", "n11", None, [stdout(0, "aa")])
    make_node(s, "n1", "n12", None, [stdout(0, "aa")])
    return s


@pytest.fixture
def sspace_fork3():
    """
        Statespace example

        n1 --0a- n11 -0c-- n111* --- n1111
           --0a- n12 -0c-- n111*
           \-0b- n13 -0c-- n111*
    """
    s = StateSpace()
    make_node(s, None, "n1")
    make_node(s, "n1", "n11", None, [stdout(0, "a")])
    make_node(s, "n1", "n12", None, [stdout(0, "a")])
    make_node(s, "n1", "n13", None, [stdout(0, "b")])
    make_node(s, "n11", "n111", None, [stdout(0, "c")])
    make_node(s, "n12", "n111", None, [stdout(0, "c")])
    make_node(s, "n13", "n111", None, [stdout(0, "c")])
    make_node(s, "n111", "n1111", None)
    return s


@pytest.fixture
def sspace_fork4():
    """
        Statespace example

        n1 --0aa- n11 -0a-- n111* -- c -- n1111
           --0a- n12 -0aa-- n111*
           \--- n13
           \--- n14 --0aaac-- n141
    """
    s = StateSpace()
    make_node(s, None, "n1")
    make_node(s, "n1", "n11", None, [stdout(0, "aa")])
    make_node(s, "n1", "n12", None, [stdout(0, "a")])
    make_node(s, "n1", "n13", None, None)
    make_node(s, "n1", "n14", None, None)
    make_node(s, "n11", "n111", None, [stdout(0, "a")])
    make_node(s, "n12", "n111", None, [stdout(0, "aa")])
    make_node(s, "n111", "n1111", None, [stdout(0, "c")])
    make_node(s, "n14", "n141", None, [stdout(0, "aaac")])
    return s


@pytest.fixture
def sspace_fork5():
    """
        Statespace example

        n1 --0aa- n11* -0aa-- n111 ---- n1111
           --0aa- n12 --- n11*
                    \-bb-- n123
    """
    s = StateSpace()
    make_node(s, None, "n1")
    make_node(s, "n1", "n11", None, [stdout(0, "aa")])
    make_node(s, "n1", "n12", None, [stdout(0, "aa")])
    make_node(s, "n11", "n111", None, [stdout(0, "aa")])
    make_node(s, "n111", "n1111", None)
    make_node(s, "n12", "n11", None)
    make_node(s, "n12", "n123", None, [stdout(0, "bb")])

    return s


@pytest.fixture
def sspace_cycle():
    """
        Statespace example

        n1 -1b- n2 -0a- n3* -1b- n4 --- n3*
                                 \----- n5
    """
    s = StateSpace()
    make_node(s, None, "n1")
    make_node(s, "n1", "n2", None, [stdout(1, "b")])
    make_node(s, "n2", "n3", None, [stdout(0, "a")])
    make_node(s, "n3", "n4", None, [stdout(1, "b")])
    make_node(s, "n4", "n3", None, None)
    make_node(s, "n4", "n5", None, [stdout(0, "ccc")])
    return s


@pytest.fixture
def sspace_complex():
    """
        Statespace example

        n1 --0a- n11 ---0ab- n111% --- n1111
           |                     \-0b- n1221*
           |-- n12 -1b- n121+ -1b- n121+
           |       |-0aab- n122 --- n1221*
           |       |        |-- n111%
           |       \-- n123
           \-0a- n1221*
    """
    s = StateSpace()

    make_node(s, None, "n1")
    make_node(s, "n1", "n11", None, [stdout(0, "a")])
    make_node(s, "n11", "n111", None, [stdout(0, "ab")])
    make_node(s, "n111", "n1111")

    make_node(s, "n1", "n12")
    make_node(s, "n12", "n121")
    make_node(s, "n121", "n121")
    make_node(s, "n12", "n122")
    make_node(s, "n12", "n123")

    make_node(s, "n122", "n1221")

    make_node(s, "n1", "n1221")
    make_node(s, "n111", "n1221")
    make_node(s, "n122", "n111")
    return s


def test_nodes_count(sspace_empty, sspace_complex, sspace_fork1):
    assert sspace_empty.nodes_count == 1
    assert sspace_complex.nodes_count == 9
    assert sspace_fork1.nodes_count == 3


def test_outputs_empty(sspace_empty):
    assert sspace_empty.get_all_outputs(STREAM_STDOUT, 0) == set(("",))


def test_outputs_fork1(sspace_fork1):
    assert sspace_fork1.get_all_outputs(STREAM_STDOUT, 0) == set(("a", "b"))


def test_outputs_fork2(sspace_fork2):
    assert sspace_fork2.get_all_outputs(STREAM_STDOUT, 0) == set(("aa",))
    assert sspace_fork2.get_outputs_count(STREAM_STDOUT, 0, 1) == 1
    assert sspace_fork2.get_outputs_count(STREAM_STDOUT, 0, 2) == 1


def test_outputs_fork3(sspace_fork3):
    assert sspace_fork3.get_all_outputs(STREAM_STDOUT, 0) == set(("ac", "bc"))


def test_outputs_fork4(sspace_fork4):
    assert sspace_fork4.get_all_outputs(STREAM_STDOUT, 0) == set(("", "aaac"))
    assert sspace_fork4.get_outputs_count(STREAM_STDOUT, 0, 1) is None
    assert sspace_fork4.get_outputs_count(STREAM_STDOUT, 0, 2) == 2
    assert sspace_fork4.get_outputs_count(STREAM_STDOUT, 0, 3) == 2


def test_outputs_fork5(sspace_fork5):
    assert sspace_fork5.get_all_outputs(STREAM_STDOUT, 0) \
        == set(("aabb", "aaaa"))
    assert sspace_fork5.get_all_outputs(STREAM_STDOUT, 0, limit=1) \
        == set(("aaaa",))
    assert sspace_fork5.get_outputs_count(STREAM_STDOUT, 0, 1) is None
    assert sspace_fork5.get_outputs_count(STREAM_STDOUT, 0, 2) == 2
    assert sspace_fork5.get_outputs_count(STREAM_STDOUT, 0, 3) == 2


def test_outputs_cycle(sspace_cycle):
    assert sspace_cycle.get_all_outputs(STREAM_STDOUT, 0) == set(("accc",))
    assert sspace_cycle.get_all_outputs(STREAM_STDOUT, 1) is None


def test_stream_of_node_empty(sspace_empty):
    node = sspace_empty.get_node_by_hash("#init#")
    assert sspace_empty.stream_to_node(node, None, STREAM_STDOUT, 0) == ""


def test_stream_of_node_fork3(sspace_fork3):
    node = sspace_fork3.get_node_by_hash("#n11#")
    assert sspace_fork3.stream_to_node(node, None, STREAM_STDOUT, 0) == "a"
    node = sspace_fork3.get_node_by_hash("#n13#")
    assert sspace_fork3.stream_to_node(node, None, STREAM_STDOUT, 0) == "b"
    node = sspace_fork3.get_node_by_hash("#n111#")
    assert sspace_fork3.stream_to_node(node, None, STREAM_STDOUT, 0) \
        in ["ac", "bc"]
