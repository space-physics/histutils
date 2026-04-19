#!/usr/bin/env python3
"""
Convert raw DMCdata from 2013-04-11 to HDF5
"""
from pathlib import Path

import histutils.dio
import histutils.rawDMCreader

# path to the data. This will probably be distinct for your computer.
fn = "~/Google Drive/My Drive/Data/PokerFlat/2013-04-11/hst/raw/2013-04-11T07-00-CamSer1387_frames_402209-1-403708.DMCdata"

# where to store the converted data
outdir = "./"

# TODO: these should be read from XML file.

params = {
    "header_bytes": 4,  # only 2011-era files have 0 header bytes.
    "xy_pixel": (512, 512),  # usually, but some files are 256x256.
    "xy_bin": (1, 1),  # usually, but some files are binned 2x2.
    "kineticsec": None,
    "rotccw": 0,
    "transpose": False,
    "flipud": False,
    "fliplr": False,
    "outfn": Path(outdir) / Path(fn).name.replace(".DMCdata", ".h5"),
}

if params["outfn"].is_file():
    raise FileExistsError(
        f"{params['outfn']} already exists. Please delete or move it before running this script."
    )

_, rawind, finf = histutils.rawDMCreader.read(fn, params)

histutils.dio.vid2h5(None, ut1=finf["ut1"], rawind=rawind, ticks=None, params=params)
