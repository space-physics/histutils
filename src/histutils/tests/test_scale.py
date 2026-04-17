#!/usr/bin/env python
import pytest
import numpy as np


def test_nearazel():
    findnearest = pytest.importorskip("histutils.findnearest")

    az = np.array([[3.0, 4, 5], [2.5, 3.5, 4.5], [2.75, 3.75, 4.75]])
    el = np.array([[1.1, 1.1, 1.1], [1.8, 1.8, 1.8], [2.5, 2.5, 2.5]])
    azpts = [3.6]
    elpts = [1.5]
    row, col = findnearest.findClosestAzel(az, el, azpts, elpts)

    assert row[0] == 1
    assert col[0] == 1
