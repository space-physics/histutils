import importlib.resources as ir
import h5py
import numpy as np

from histutils.rawDMCreader import read, getDMCparam, frame2ut1
from histutils.dio import vid2h5
from histutils.index import getRawInd
from histutils.hstxmlparse import xmlparam
from histutils.timedmc import parse_gprmc, iso_to_epoch


# dummy test parameters
def get_params() -> tuple:

    with ir.path(__package__, "testframes.DMCdata") as rawfn:
        x = xmlparam(rawfn.with_suffix(".xml"))

        params = {
            "kineticsec": x["kineticrate"],
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

    tReq = ("2013-04-11T10:43:34.6648", "2013-04-11T10:43:34.6837")
    tUnix = iso_to_epoch(tReq[0]), iso_to_epoch(tReq[1])
    assert tUnix == (1365677014.6648, 1365677014.6837)  # sanity check

    outfn = tmp_path / "testframes.h5"

    i0, iend = getRawInd(rawfn, params)
    print(f"first raw frame index: {i0}, last raw frame index: {iend}")

    assert i0 == 710730
    assert iend == 710731

    iraw = np.arange(i0, iend + 1)

    tUTC = frame2ut1(params["startUTC"], params["kineticsec"], iraw)
    # 1365677014.6648664 datetime(2013, 4, 11, 10, 43, 34, 664866)
    # 1365677014.683734  datetime(2013, 4, 11, 10, 43, 34, 683734)

    i = (tUTC >= tUnix[0]) & (tUTC < tUnix[1])

    iraw = iraw[i]
    params["frameindrel"] = params["frameindrel"][i]
    params["nframeextract"] = iraw.size
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

    i0, iend = getRawInd(rawfn, params)
    print(f"first raw frame index: {i0}, last raw frame index: {iend}")

    assert i0 == 710730
    assert iend == 710731

    iraw = np.arange(i0, iend + 1)

    vid2h5(rawfn, outfn, iraw, params)

    assert outfn.is_file()
