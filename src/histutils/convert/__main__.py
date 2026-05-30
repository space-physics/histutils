#!/usr/bin/env python3
"""
Convert raw DMCdata to HDF5
"""

from argparse import Namespace
from pathlib import Path
from typing import Any
from pprint import pprint
import numpy as np

from ..timedmc import parse_gprmc, iso_to_epoch
from ..rawDMCreader import getDMCparam
from ..index import getRawInd
from ..dio import vid2h5, frame2ut1
from ..hstxmlparse import xmlparam


def convert_DMC_to_hdf5(
    rawFile: Path,
    outFile: Path,
    params: dict[str, Any],
    tReq: tuple[str, str] | None = None,
) -> None:
    """
    converts .DMCdata files to .h5 files, with metadata
    """

    if "startUTC" not in params:
        if params.get("nmeaFile") is None:
            nmeaFile = rawFile.with_suffix(".nmea")
        gpsInfo = parse_gprmc(nmeaFile)
        params["startUTC"] = gpsInfo

    if params.get("xmlFile") is None:
        xmlFile = rawFile.with_suffix(".xml")
    x = xmlparam(xmlFile)

    params["xy_pixel"] = (x["horizpixels"], x["vertpixels"])
    params["xy_bin"] = (x["binning"], x["binning"])

    if params.get("kineticsec") is None:
        params["kineticsec"] = x["kineticrate"]

    fInfo = getDMCparam(rawFile, params)
    params.update(fInfo)

    pprint(params)

    if outFile.is_file():
        raise FileExistsError(
            f"{outFile} already exists. Please delete or move it before running this script."
        )

    i0, iend = getRawInd(rawFile, params)
    print(f"first raw frame index: {i0}, last raw frame index: {iend}")
    iraw = np.arange(i0, iend + 1)

    tUTC = frame2ut1(params["startUTC"], params["kineticsec"], iraw)
    print(f"raw frames cover {tUTC[0]} to {tUTC[-1]}")

    if tReq is not None:
        i = (tUTC >= iso_to_epoch(tReq[0])) & (tUTC <= iso_to_epoch(tReq[1]))
        iraw = iraw[i]

    vid2h5(rawFile, outFile, rawind=iraw, params=params)


def parse_cli() -> Namespace:
    from argparse import ArgumentParser

    p = ArgumentParser(description="Raw .DMCdata file reader, plotter, converter")
    p.add_argument("rawfile", help=".DMCdata file name and path")
    p.add_argument("outfile", help="extract raw data into this path (dir or filename)")
    p.add_argument(
        "--nmeaFile", help="nmea filepath to parse GPS info from, if not same stem as infile"
    )
    p.add_argument(
        "--xmlFile", help="xml filepath to parse camera info from, if not same stem as infile"
    )
    p.add_argument(
        "-t",
        "--ut1",
        help="UT1 times (seconds since Jan 1 1970) to request (parseable string ISO time)",
        metavar=("start", "stop"),
        nargs=2,
    )
    p.add_argument(
        "--header_bytes",
        help="number of header bytes: 2013-2016: 4  2011: 0",
        type=int,
        default=4,
    )
    P = p.parse_args()
    return P


if __name__ == "__main__":
    args = parse_cli()
    convert_DMC_to_hdf5(Path(args.rawfile), Path(args.outfile), params=vars(args), tReq=args.ut1)
