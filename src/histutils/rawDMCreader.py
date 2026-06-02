"""
reads .DMCdata files and displays them

NOTE: Observe the dtype=np.int64, this is for Windows Python, that wants to
   default to int32 instead of int64 like everyone else!
"""

from pathlib import Path
import logging
import typing as T
import math

import numpy as np
import numpy.typing as npt

from .index import get_raw_index, meta2rawInd, req2frame
from .timedmc import frame2ut1, ut12frame

BPP = 16  # bits per pixel


class DMCFileInfo(T.TypedDict):
    Nmeta: int
    header_bytes: int
    xy_actual: tuple[int, int]
    xy_pixel: T.NotRequired[tuple[int, int]]
    xy_bin: T.NotRequired[tuple[int, int]]
    image_pixels: int
    image_bytes: int
    frame_bytes: int
    Nframe_extract: T.NotRequired[int]
    i_rel: T.NotRequired[np.ndarray]
    ut1: T.NotRequired[np.ndarray]
    startUTC: T.NotRequired[np.datetime64]
    spool_file: T.NotRequired[Path]
    kinetic_sec: T.NotRequired[float]
    transpose: bool
    rotccw: int
    flipud: bool
    fliplr: bool
    sensor_lla: T.NotRequired[tuple[float, float, float]]


def read(infn: str | Path, params: DMCFileInfo) -> tuple[np.ndarray, np.ndarray, DMCFileInfo]:
    """
    return data as variable - the variable can be very large.
    """

    fn = Path(infn).expanduser()
    # %% setup data parameters
    # preallocate *** LABVIEW USES ROW-MAJOR ORDERING C ORDER
    finf = getDMCparam(fn, params)  # type: ignore

    rawFrameInd = np.zeros(finf["Nframe_extract"], dtype=np.int64)
    # %% output (variable or file) - script should fail here if inadequate RAM
    data = np.zeros(
        (finf["Nframe_extract"], *finf["xy_actual"]),
        dtype=np.uint16,
        order="C",
    )
    # %% read image stack to NDarray
    with fn.open("rb") as fid:
        # j and i are NOT the same in general when not starting from beginning of file!
        for j, i in enumerate(finf["i_rel"]):
            D, rawFrameInd[j] = getDMCframe(fid, i, finf)
            data[j, ...] = D
    # %% absolute time estimate, software timing
    finf["ut1"] = frame2ut1(params["startUTC"], params["kinetic_sec"], rawFrameInd)

    return data, rawFrameInd, finf


def getDMCparam(fn: Path, params: dict[str, T.Any]) -> DMCFileInfo:
    """
    header_bytes=4 for 2013-2016 data
    header_bytes=0 for 2011 data
    """

    xy_actual = (
        params["xy_pixel"][0] // params["xy_bin"][0],
        params["xy_pixel"][1] // params["xy_bin"][1],
    )

    finf: DMCFileInfo = {
        "Nmeta": params["header_bytes"] // 2,
        "header_bytes": params["header_bytes"],
        "xy_actual": xy_actual,
        "image_pixels": math.prod(xy_actual),
        "image_bytes": math.prod(xy_actual) * BPP // 8,
        "frame_bytes": math.prod(xy_actual) * BPP // 8 + params["header_bytes"],
        "transpose": False,
        "rotccw": 0,
        "flipud": False,
        "fliplr": False,
    }

    params.update(finf)

    FrameIndRel = whichframes(fn, params)

    finf["Nframe_extract"] = FrameIndRel.size
    finf["i_rel"] = FrameIndRel

    return finf


def whichframes(fn: Path, params: dict[str, T.Any]) -> npt.NDArray[np.integer]:
    """
    Computes the frame indices to extract from the .DMCdata file, based on the requested time range or frame range.
    These are frame indices relative to the first frame in the file, and are used for indexing into the raw data.
    """

    if not fn.is_file():
        raise FileNotFoundError(fn)

    fileSizeBytes = fn.stat().st_size

    if fileSizeBytes < params["image_bytes"]:
        raise ValueError(f"File size {fileSizeBytes} is smaller than a single image frame.")

    if fileSizeBytes % params["frame_bytes"]:
        logging.error(
            "Either the file is truncated, or I am not reading this file correctly."
            f"\n bytes per frame: {params['frame_bytes']:d}"
        )

    first_frame, last_frame = get_raw_index(fn, params["Nmeta"], params["image_bytes"])

    if fn.suffix == ".DMCdata":
        nFrame = fileSizeBytes // params["frame_bytes"]
        logging.info(f"{nFrame} frames, Bytes: {fileSizeBytes} in file {fn}")

        nFrameRaw = last_frame - first_frame + 1
        if nFrameRaw != nFrame:
            logging.warning(f"there may be missed frames: nFrameRaw {nFrameRaw}   nFrame {nFrame}")
    else:  # CMOS
        nFrame = last_frame - first_frame + 1

    allrawframe = np.arange(first_frame, last_frame + 1, 1, dtype=np.int64)
    logging.info(f"first / last raw frame #'s: {first_frame}  / {last_frame} ")
    # %% absolute time estimate
    ut1_unix_all = frame2ut1(params["startUTC"], params["kinetic_sec"], allrawframe)
    # %% setup frame indices
    """
    if no requested frames were specified, read all frames.
    Otherwise, just return the requested frames.
    Assignments have to be "int64", not just python "int", because Windows
        Python 2.7 64-bit on files >2.1GB, the bytes will wrap
    """
    i_rel: npt.NDArray[np.integer] | None = None
    if "ut1req" in params:
        i_rel = ut12frame(params["ut1req"], np.arange(0, nFrame, 1, dtype=np.int64), ut1_unix_all)

    if i_rel is None or i_rel.size == 0:
        # NOTE: no ut1req or problems with ut1req, canNOT use else, need to test len() in case index is [0] validly
        if "frame_request" in params:
            i_rel = req2frame(params["frame_request"], nFrame)
        else:
            i_rel = np.arange(nFrame, dtype=np.int64)

    badReqInd = (i_rel > nFrame) | (i_rel < 0)
    # check if we requested frames beyond what the BigFN contains
    if badReqInd.any():
        # don't include frames in case of None
        raise ValueError(f"frames requested outside the times covered in {fn}")

    nFrameExtract = i_rel.size  # to preallocate properly
    bytes_extract = nFrameExtract * params["frame_bytes"]
    logging.info(
        f"Extracting {nFrameExtract} frames from {fn} totaling {bytes_extract / 1e9:.2f} GB."
    )

    return i_rel


def getDMCframe(
    f: T.Union[T.BinaryIO, Path], iFrm: int, finf: DMCFileInfo
) -> tuple[np.ndarray, int]:
    """
    read a single image frame

    Parameters
    ----------
    f: pathlib.Path or BinaryIO
        open file handle or file path
    """
    if isinstance(f, Path):
        if not f.is_file():  # need for Windows PermissionError
            raise FileNotFoundError(f)
        with f.open("rb") as g:
            return getDMCframe(g, iFrm, finf)
    # on windows, "int" is int32 and overflows at 2.1GB!  We need np.int64
    currByte = iFrm * finf["frame_bytes"]
    # %% advance to start of frame in bytes
    logging.debug(f"seeking to byte {currByte}")

    if not isinstance(iFrm, (int, np.int64)):
        raise TypeError("int32 will fail on files > 2GB")

    try:
        f.seek(currByte, 0)
    except OSError as e:
        raise OSError(
            f"could not seek to byte {currByte:d}. try using a 64-bit integer for iFrm \n"
            f"is {f.name} a DMCdata file?  {e}"
        )
    # %% read data ***LABVIEW USES ROW-MAJOR C ORDERING!!
    try:
        currFrame = np.fromfile(f, np.uint16, finf["image_pixels"]).reshape(
            finf["xy_actual"][::-1], order="C"
        )
    except ValueError as e:
        raise ValueError(f"read past end of file? \n {f.name} \n {e}")

    rawFrameInd = meta2rawInd(f, finf["Nmeta"])

    if rawFrameInd < 1:  # 2011 no metadata file
        rawFrameInd = iFrm + 1  # fallback

    return currFrame, rawFrameInd
