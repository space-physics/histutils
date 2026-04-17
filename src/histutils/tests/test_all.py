#!/usr/bin/env python
from pathlib import Path
import numpy as np

from histutils.rawDMCreader import goRead

R = Path(__file__).parent


def test_rawread():
    bigfn = R / "testframes.DMCdata"

    params = {
        "xy_pixel": (512, 512),
        "xy_bin": (1, 1),
        "frame_request": (1, 2, 1),
        "header_bytes": 4,
    }

    testframe, testind, finf = goRead(bigfn, params)

    # these are both tested by goRead
    # finf = getDMCparam(bigfn,(512,512),(1,1),None,verbose=2)
    # with open(bigfn,'rb') as f:
    #    testframe,testind = getDMCframe(f,iFrm=1,finf=finf,verbose=2)
    # test a handful of pixels

    assert testind.dtype == np.int64
    assert testframe.dtype == np.uint16
    assert testind == 710730
    assert (testframe[0, :5, 0] == [956, 700, 1031, 730, 732]).all()
    assert (testframe[0, -5:, -1] == [1939, 1981, 1828, 1752, 1966]).all()
