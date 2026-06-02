import importlib.resources as ir
import functools

from pytest import approx
import h5py
import numpy as np

from histutils.rawDMCreader import read, getDMCparam, frame2ut1
from histutils.dio import vid2h5
from histutils.index import get_raw_index
from histutils.hstxmlparse import xmlparam
from histutils.timedmc import parse_gprmc


# dummy test parameters
@functools.cache
def get_params() -> tuple:

    with ir.path(__package__, "testframes.DMCdata") as rawfn:
        x = xmlparam(rawfn.with_suffix(".xml"))

        params = {
            "kinetic_sec": x["kineticrate"],
            "xy_pixel": (x["horizpixels"], x["vertpixels"]),
            "xy_bin": (x["binning"], x["binning"]),
            "header_bytes": 4,
        }

        # "rotccw": 0,  # counter clockwise rotation in degrees
        # "transpose": False,
        # "flipud": False,  # flip up down
        # "fliplr": False,  # flip left right

        gpsInfo = parse_gprmc(rawfn.with_suffix(".nmea"))
        params["startUTC"] = gpsInfo

        fInfo = getDMCparam(rawfn, params)
        params.update(fInfo)

        return rawfn, params


def test_raw_index():
    rawfn, params = get_params()

    i0, iend = get_raw_index(rawfn, params["Nmeta"], params["image_bytes"])
    assert i0 == 710730
    assert iend == 710731


def test_raw_read():
    rawfn, params = get_params()

    # arbitrary for test
    params["frame_request"] = (1, 2, 1)

    testframe, testind, _ = read(rawfn, params)

    assert testind.dtype == np.int64
    assert testframe.dtype == np.uint16

    # %% verify a handful of pixels
    assert testind == 710730
    assert (testframe[0, :5, 0] == [956, 700, 1031, 730, 732]).all()
    assert (testframe[0, -5:, -1] == [1939, 1981, 1828, 1752, 1966]).all()


def test_convert_range(tmp_path):
    rawfn, params = get_params()

    tReq = (np.datetime64("2013-04-11T10:43:34.6648"), np.datetime64("2013-04-11T10:43:34.6837"))

    outfn = tmp_path / "testframes.h5"

    i0, iend = get_raw_index(rawfn, params["Nmeta"], params["image_bytes"])
    print(f"first raw frame index: {i0}, last raw frame index: {iend}")

    assert i0 == 710730
    assert iend == 710731

    iraw = np.arange(i0, iend + 1)

    tUTC = frame2ut1(params["startUTC"], params["kinetic_sec"], iraw)
    # 1365677014.6648664 datetime(2013, 4, 11, 10, 43, 34, 664866)
    # 1365677014.6837339 datetime(2013, 4, 11, 10, 43, 34, 683734)
    print(f"file UTC: {tUTC[0]} to {tUTC[-1]}  startUTC: {params['startUTC']} kinetic_sec: {params['kinetic_sec']}")
    assert tUTC[0] == approx(np.datetime64("2013-04-11T10:43:34.6648664"))
    assert tUTC[-1] == approx(np.datetime64("2013-04-11T10:43:34.6837339"))

    i = (tUTC >= tReq[0]) & (tUTC < tReq[1])

    iraw = iraw[i]

    print(f"requested time range corresponds to {i.sum()} frames {iraw}")

    params["i_rel"] = params["i_rel"][i]
    params["Nframe_extract"] = iraw.size
    assert iraw.size == 1

    vid2h5(rawfn, outfn, iraw, params)

    assert outfn.is_file()

    with h5py.File(outfn, "r") as f:
        assert f["/rawind"].shape[0] == 1
        assert f["/rawind"].shape[0] == f["/rawimg"].shape[0]
        assert f["/rawind"][0] == 710730
        assert f["/rawind"][-1] == 710730


def test_convert_all(tmp_path):
    rawfn, params = get_params()

    outfn = tmp_path / "testframes.h5"

    i0, iend = get_raw_index(rawfn, params["Nmeta"], params["image_bytes"])
    print(f"first raw frame index: {i0}, last raw frame index: {iend}")

    assert i0 == 710730
    assert iend == 710731

    iraw = np.arange(i0, iend + 1)

    vid2h5(rawfn, outfn, iraw, params)

    assert outfn.is_file()
