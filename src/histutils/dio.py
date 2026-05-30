from pathlib import Path
from typing import Any
from datetime import datetime

import numpy as np
import numpy.typing as npt
import h5py

from .timedmc import frame2ut1
from .rawDMCreader import getDMCframe


def dir2fn(ofn: Path, ifn: Path, suffix: str = ".h5") -> Path:
    """

    Parameters
    ----------

    ofn: pathlib.Path
        filename or output directory, to create filename based on ifn
    ifn: pathlib.Path
        input filename (don't overwrite!)
    suffix: str, optional
        desired file extension e.g. .h5

    Returns
    -------

    ofn: pathlib.Path
        filename to write
    """

    ofn = Path(ofn).expanduser()
    ifn = Path(ifn).expanduser()
    if not ifn.is_file():
        raise FileNotFoundError(ifn)

    if ofn.is_dir():
        ofn = ofn / ifn.with_suffix(suffix).name

    if ofn.is_file() and ofn.samefile(ifn):
        raise FileExistsError(f"do not overwrite input file! {ifn}")

    return ofn


def imgwriteincr(fn: Path, imgs, imgslice: int | slice):
    """
    writes HDF5 huge image files in increments

    Parameters
    ----------

    fn: pathlib.Path
        HDF5 filename to write / append to
    imgs: numpy.ndarray
        image(s) N x X x Y to write
    imgslice: int or slice
        where to write the image(s) in the HDF5 file
    """
    if isinstance(imgslice, int):
        if imgslice and not (imgslice % 2000):
            print(f"appending images {imgslice} to {fn}")

    if isinstance(fn, Path):
        # avoid accidental overwriting of source file due to misspecified command line
        with h5py.File(fn, "r+") as f:
            f["/rawimg"][imgslice, :, :] = imgs
    elif isinstance(fn, h5py.File):
        fn["/rawimg"][imgslice, :, :] = imgs
    else:
        raise TypeError(f"{fn} must be Path or h5py.File instead of {type(fn)}")


def vid2h5(
    inFile: Path | str,
    outFile: Path | str,
    rawind: npt.NDArray[np.integer],
    params: dict[str, Any],
    *,
    ticks: npt.NDArray[np.integer] | None = None,
    i: int = 0,
    Nfile: int = 1,
    cmdlog: str | None = None,
) -> None:
    """
    convert .DMCdata raw image to compressed Image format HDF5 file

    Parameters
    ----------

    inFile: pathlib.Path or str
        input .DMCdata filename to read
    outFile: pathlib.Path or str
        output .h5 filename to write, or directory to create filename based on input
    rawind: numpy array of integers
        one-based index since camera program started this session.
    params: dict
        parameters for reading and writing, see get_params() in test_rw.py for example
    """

    inFile = Path(inFile).expanduser().resolve(strict=True)

    outFile = Path(outFile).expanduser().resolve(strict=False)
    if outFile.is_dir():
        raise IsADirectoryError(outFile)

    if rawind is None or rawind.size == 0:
        raise ValueError(
            "rawind must be a non-empty array of integers"
            ", one-based index since camera program started this session."
        )

    # if line wraps (>80 characters), this in-place update breaks.
    txtupd = f"converting {inFile} "
    if params.get("spoolfn"):
        txtupd += f"convert file {i + 1} / {Nfile}  {params['spoolfn'].name}"
    txtupd += f" => {outFile}"
    print(txtupd + "\r", end="")
    # %% saving
    """
    Reference: https://www.hdfgroup.org/HDF5/doc/ADGuide/ImageSpec.html
    Thanks to Eric Piel of Delmic for pointing out this spec
    * the HDF5 attributes set are necessary to put HDFView into image mode and enables
    other conforming readers to easily play images stacks as video.
    """
    # NOTE write mode r+ to not overwrite incremental images
    writemode = "r+" if outFile.is_file() else "w"

    tUTC = frame2ut1(params["startUTC"], params["kineticsec"], rawind)

    print(f"writing {outFile} from {tUTC[0]} to {tUTC[-1]}")

    NframeExtract = rawind[-1] - rawind[0] + 1

    if "rotccw" not in params:
        params["rotccw"] = 0  # counter clockwise rotation in degrees
    if "transpose" not in params:
        params["transpose"] = False
    if "flipud" not in params:
        params["flipud"] = False  # flip up down
    if "fliplr" not in params:
        params["fliplr"] = False  # flip left right

    # %% Convert raw DMCdata to HDF5, frame by frame to save RAM
    with h5py.File(outFile, writemode) as f:
        # %% initialize datasets and attributes
        if "header" not in f and "header" in params:
            f["/header"] = str(params["header"])

        if "hdf5version" not in f:
            f["/hdf5version"] = h5py.version.hdf5_version_tuple

        if "cmdlog" not in f:
            if isinstance(cmdlog, (tuple, list)):
                cmdlog = " ".join(cmdlog)
            f["/cmdlog"] = str(cmdlog)

        if "params" not in f:
            cparam = np.array(
                (
                    params["kineticsec"],
                    params["rotccw"],
                    params["transpose"],
                    params["flipud"],
                    params["fliplr"],
                    1,
                ),
                dtype=[
                    ("kineticsec", "f8"),
                    ("rotccw", "i1"),
                    ("transpose", "i1"),
                    ("flipud", "i1"),
                    ("fliplr", "i1"),
                    ("questionable_ut1", "i1"),
                ],
            )
            # cannot use fletcher32 here, Typeerror
            f.create_dataset("/params", data=cparam)

        if "sensorloc" not in f and "sensorloc" in params:
            loc = params["sensorloc"]
            lparam = np.array(
                (loc[0], loc[1], loc[2]),
                dtype=[("lat", "f8"), ("lon", "f8"), ("alt_m", "f8")],
            )

            # cannot use fletcher32 here, Typeerror
            Ld = f.create_dataset("/sensorloc", data=lparam)
            Ld.attrs["units"] = "WGS-84 lat (deg),lon (deg), altitude (meters)"

        if rawind is not None:
            if "rawind" not in f:  # first pass
                fri = f.create_dataset(
                    "/rawind", shape=(NframeExtract,), dtype=np.int64, fletcher32=True
                )
                fri.attrs["units"] = "one-based index since camera program started this session"

        if "rawimg" not in f:  # first pass
            setupimgh5(f, params)

        if "ut1_unix" not in f:  # first pass
            fut1 = f.create_dataset(
                "/ut1_unix", shape=(NframeExtract,), dtype=float, fletcher32=True
            )
            fut1.attrs["units"] = "seconds since Unix epoch Jan 1 1970 midnight"

        if ticks is not None:
            if "ticks" not in f:
                ftk = f.create_dataset(
                    "/ticks", shape=(NframeExtract,), dtype=np.uint64, fletcher32=True
                )
                ftk.attrs["units"] = "FPGA tick counter for each image frame"

        if params.get("spoolfn"):
            # http://docs.h5py.org/en/latest/strings.html
            if "spoolfn" not in f:
                fsp = f.create_dataset(
                    "/spoolfn", shape=(NframeExtract,), dtype=h5py.special_dtype(vlen=bytes)
                )
                fsp.attrs["description"] = "input filename data was extracted from"

        with inFile.open("rb") as fid:
            # j and i are NOT the same in general when not starting from beginning of file!
            for j, i in enumerate(params["frameindrel"]):
                if j and not (j % 10):
                    print(f"writing frame {j} of {NframeExtract} to {outFile}\r", end="")

                imgFrame, rawFrameInd = getDMCframe(fid, i, params)

                f["/rawimg"][j, ...] = imgFrame
                f["/rawind"][j] = rawFrameInd
                f["/ut1_unix"][j] = tUTC[j]

                if ticks is not None:
                    f["/ticks"][j] = ticks[j]

                if params.get("spoolfn"):
                    f["/spoolfn"][j] = params["spoolfn"][j].name


def setupimgh5(
    f: Path | h5py.File,
    params: dict[str, int],
    *,
    dtype=np.uint16,
    writemode: str = "r+",
    key: str = "/rawimg",
    cmdlog: str | None = None,
):
    """
    Configures an HDF5 file for storing image stacks, enabling video player in
    HDF5 readers so equipped

    Parameters
    ----------
    f: HDF5 handle (or filename)

    h: HDF5 dataset handle
    """
    if isinstance(f, (str, Path)):  # assume new HDF5 file wanted
        f = Path(f).expanduser()
        if f.is_dir():
            raise IsADirectoryError(f)
        if not f.is_file():
            writemode = "w"

        with h5py.File(f, writemode) as F:
            setupimgh5(F, params, dtype=dtype, writemode=writemode, key=key)

    elif isinstance(f, h5py.File):
        Nrow, Ncol = params["super_y"], params["super_x"]

        h = f.create_dataset(
            key,
            shape=(params["nframeextract"], Nrow, Ncol),
            dtype=dtype,
            chunks=(1, Nrow, Ncol),  # each image is a chunk
            compression="gzip",
            # no difference in filesize from 1 to 5, except much faster to use lower numbers!
            compression_opts=1,
            shuffle=True,
            fletcher32=True,
            track_times=True,
        )
        h.attrs["CLASS"] = np.bytes_("IMAGE")
        h.attrs["IMAGE_VERSION"] = np.bytes_("1.2")
        h.attrs["IMAGE_SUBCLASS"] = np.bytes_("IMAGE_GRAYSCALE")
        h.attrs["DISPLAY_ORIGIN"] = np.bytes_("LL")
        h.attrs["IMAGE_WHITE_IS_ZERO"] = np.uint8(0)

        if cmdlog and isinstance(cmdlog, str):
            f["/cmdlog"] = cmdlog
    else:
        raise TypeError(f"{type(f)} is not correct, must be filename or h5py.File HDF5 file handle")
