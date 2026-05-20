#!/usr/bin/env python3
"""
Convert raw DMCdata from 2013-04-11 to HDF5
"""
from pathlib import Path
from pprint import pprint

import histutils.dio
import histutils.index
import histutils.timedmc
import histutils.rawDMCreader
from histutils.hstxmlparse import xmlparam

# path to the data. This will probably be distinct for your computer.
data_path = Path("~/Library/CloudStorage/GoogleDrive-mhirsch@bu.edu/My Drive/Data/PokerFlat/2013-04-11/hst/raw").expanduser()

fn = data_path / "2013-04-11T07-00-CamSer1387_frames_402209-1-403708.DMCdata"


ut1Req = ("2013-04-11T07:00:00Z", "2013-04-11T07:00:05Z")
# UTC time range to extract, in ISO format

# where to store the converted data
outdir = Path("./").expanduser()

outfn = outdir / fn.name.replace(".DMCdata", ".h5")
xmlfn = data_path / "2013-04-11T07-00-CamSer1387.xml"
nmeafn = xmlfn.with_suffix(".nmea")

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

gpsInfo = histutils.timedmc.parse_gprmc(nmeafn)
params["startUTC"] = gpsInfo

fInfo = histutils.rawDMCreader.getDMCparam(fn, params)
params.update(fInfo)

pprint(params)

if outfn.is_file():
    raise FileExistsError(
        f"{outfn} already exists. Please delete or move it before running this script."
    )

i0, iend = histutils.index.getRawInd(fn, params)
print(f"first raw frame index: {i0}, last raw frame index: {iend}")

histutils.dio.vid2h5(fn, ut1=ut1Req, rawind=(i0, iend), outfn=outfn, params=params)
