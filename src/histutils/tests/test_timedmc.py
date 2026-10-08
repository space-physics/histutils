import numpy as np
import pytest

from histutils.timedmc import nearest1d, ut12frame


@pytest.mark.parametrize("ut1_unix", [None, np.array([0.0, 1.0, 2.0])])
def test_ut12frame_no_time_request(ut1_unix):
    ind = np.array([5, 6, 7], dtype=np.int64)

    assert ut12frame(None, ind, ut1_unix) is None


def test_nearest1d_tie_breaks_to_lower_index():
    xref = np.array([0.0, 1.0, 2.0, 3.0])
    xq = np.array([0.49, 0.5, 2.6])

    nearest = nearest1d(xref, xq)

    assert np.array_equal(nearest, np.array([0, 0, 3]))


def test_ut12frame_nearest_neighbor_ties_pick_earlier():
    ut1_unix = np.array([0.0, 1.0, 2.0, 3.0])
    ind = np.array([10, 11, 12, 13])

    framereq = ut12frame([0.49, 0.5, 1.51], ind, ut1_unix)

    assert framereq is not None
    assert np.array_equal(framereq, np.array([10, 10, 12]))


def test_ut12frame_discards_outside_range():
    ut1_unix = np.array([0.0, 1.0, 2.0])
    ind = np.array([5, 6, 7])

    framereq = ut12frame([-1.0, 0.0, 1.0, 3.0], ind, ut1_unix)

    assert framereq is not None
    assert np.array_equal(framereq, np.array([5, 6]))
