#!/usr/bin/env python3
"""
Convert raw DMCdata from 2013-04-11 to HDF5
"""

from pathlib import Path
from pprint import pprint
import argparse

import numpy as np

import histutils.dio
import histutils.index
import histutils.timedmc as hstt
import histutils.rawDMCreader
from histutils.hstxmlparse import xmlparam

parser = argparse.ArgumentParser(description="Convert raw DMCdata to HDF5")
parser.add_argument("inFile", help="input .DMCdata filename to read")
parser.add_argument("outDir", help="output HDF5 directory to write, or filename to write")
args = parser.parse_args()

# path to the data. This will probably be distinct for your computer.
in_path = Path(args.inFile).expanduser() / "Data/PokerFlat/2013-04-11/hst/raw"
rawfn = in_path / "2013-04-11T07-00-CamSer1387_frames_402209-1-403708.DMCdata"
# This file contains data from
# 2013‑04‑11T10:43:31.374734Z
# to
# 2013‑04‑11T10:44:21.339319Z

tReq = ("2013-04-11T10:43:35", "2013-04-11T10:44:00")
# UTC time range to extract, in ISO format
# if omitted, convert whole file, which is general can be 100+ Gigabyte

# where to store the converted data
outDir = Path(args.outDir).expanduser()
outFile = outDir / rawfn.with_suffix(".h5").name

xmlfn = in_path / "2013-04-11T07-00-CamSer1387.xml"
nmeafn = xmlfn.with_suffix(".nmea")

x = xmlparam(xmlfn)

# only 2011-era files have 0 header_bytes. Newer have 4 header_bytes.

params = {
    "header_bytes": 4,  # only 2011-era files have 0 header_bytes. Newer have 4 header_bytes.
    "xy_pixel": (x["horizpixels"], x["vertpixels"]),
    "xy_bin": (x["binning"], x["binning"]),
    "kineticsec": x["kineticrate"],
    "rotccw": 0,  # counter clockwise rotation in degrees
    "transpose": False,
    "flipud": False,  # flip up down
    "fliplr": False,  # flip left right
}

gpsInfo = hstt.parse_gprmc(nmeafn)
params["startUTC"] = gpsInfo

fInfo = histutils.rawDMCreader.getDMCparam(rawfn, params)
params.update(fInfo)

pprint(params)

if outFile.is_file():
    raise FileExistsError(
        f"{outFile} already exists. Please delete or move it before running this script."
    )

i0, iend = histutils.index.getRawInd(rawfn, params)
print(f"first raw frame index: {i0}, last raw frame index: {iend}")
iraw = np.arange(i0, iend + 1)

tUTC = histutils.dio.frame2ut1(params["startUTC"], params["kineticsec"], iraw)
print(f"raw frames cover {tUTC[0]} to {tUTC[-1]}")

i = (tUTC >= hstt.iso_to_epoch(tReq[0])) & (tUTC <= hstt.iso_to_epoch(tReq[1]))
ireq = iraw[i]

histutils.dio.vid2h5(rawfn, outFile, rawind=ireq, params=params)
