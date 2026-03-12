from pytest import approx
import pytest
import shutil

from histutils.hstxmlparse import xmlparam
import histutils.utils as hu

import importlib.resources as ir


def test_xmlparse():
    fn = ir.files("histutils.tests") / "testframes.xml"
    params = xmlparam(fn)

    assert params["binning"] == 1
    assert params["kineticrate"] == approx(1.88674795e-2)


def test_quota_too_small(tmp_path):
    freeout = shutil.disk_usage(tmp_path).free

    test_fn = tmp_path / "fake_file"

    too_small = max(
        0, freeout - 9e9
    )  # handles where drive already has less than 10 GB free
    with pytest.raises(OSError):
        hu.write_quota(too_small, test_fn)

    with pytest.raises(ValueError):
        hu.write_quota(-1, test_fn)


def test_quota_ok(tmp_path):
    freeout = shutil.disk_usage(tmp_path).free
    test_fn = tmp_path / "fake_file"

    if freeout > 10e9:
        assert hu.write_quota(0, test_fn) == freeout
    else:
        pytest.skip("not enough free space")
