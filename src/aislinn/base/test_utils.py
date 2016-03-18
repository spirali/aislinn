
from utils import Intervals


def test_intervals():
    ii = Intervals()

    assert ii.add(10, 20) == [(10, 20)]
    assert ii.add(20, 30) == [(20, 30)]
    assert ii.add(50, 60) == [(50, 60)]

    assert ii.add(10, 20) == []
    assert ii.add(10, 30) == []
    assert ii.add(15, 16) == []

    assert ii.add(10, 100) == [(30, 50), (60, 100)]
    assert ii.add(5, 100) == [(5, 10)]
    assert ii.remove(5, 100) == [(5, 10)]
