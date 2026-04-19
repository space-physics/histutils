#!/usr/bin/env python3
"""
Convert raw DMCdata from 2013-04-11 to HDF5
"""
from pathlib import Path
from pprint import pprint

import histutils.dio
import histutils.rawDMCreader
from histutils.hstxmlparse import xmlparam

# path to the data. This will probably be distinct for your computer.
fn = Path(
    "~/Google Drive/My Drive/Data/PokerFlat/2013-04-11/hst/raw/2013-04-11T07-00-CamSer1387_frames_402209-1-403708.DMCdata"
)

# where to store the converted data
outdir = Path("./").expanduser()

outfn = outdir / fn.name.replace(".DMCdata", ".h5")
xmlfn = Path(
    "~/Google Drive/My Drive/Data/PokerFlat/2013-04-11/hst/raw/2013-04-11T07-00-CamSer1387.xml"
).expanduser()

x = xmlparam(xmlfn)

# only 2011-era files have 0 header_bytes. Newer have 4 header_bytes.

params = {
    "header_bytes": 4,  # only 2011-era files have 0 header_bytes. Newer have 4 header_bytes.
    "xy_pixel": (x["horizpixels"], x["vertpixels"]),
    "xy_bin": (x["binning"], x["binning"]),  # usually, but some files are binned 2x2.
    "kineticsec": x["kineticrate"],
    "rotccw": 0,  # counter clockwise rotation in degrees
    "transpose": False,
    "flipud": False,  # flip up down
    "fliplr": False,  # flip left right
}

pprint(params)

if outfn.is_file():
    raise FileExistsError(
        f"{outfn} already exists. Please delete or move it before running this script."
    )

_, rawind, finf = histutils.rawDMCreader.read(fn, params, outfn)

histutils.dio.vid2h5(None, ut1=finf["ut1"], rawind=rawind, ticks=None, outfn=outfn, params=params)
