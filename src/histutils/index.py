from pathlib import Path
from struct import pack, unpack

import numpy as np
import numpy.typing as npt


def get_raw_index(fn: Path, Nmeta: int, image_bytes: int) -> tuple[int, int]:
    """
    get the first and last raw image video frame indices from .DMCdata file
    The data format writes an image frame, then one-based frame index.
    The end of the file is the last image frame index.

    Nmeta: int
      number of metadata entries per frame.
    """

    if Nmeta < 1:
        # %% 2011 old files, no header, only raw images
        file_bytes = fn.stat().st_size
        if file_bytes % image_bytes:
            raise ValueError(f"{fn} mismatch frame->file size")

        iStart = 1  # definition, one-based indexing
        iEnd = file_bytes // image_bytes
    else:
        # %% DMC / HiST 2013-2016
        with fn.open("rb") as f:
            f.seek(image_bytes, 0)
            iStart = meta2rawInd(f, Nmeta)

            if iStart < 1:
                raise ValueError(f"first index must be at least one, got {iStart}")
            if iStart > 100_000_000:
                raise ValueError(f"first index seems impossibly large: {iStart}")
            # %% end frame
            f.seek(-Nmeta * 2, 2)
            iEnd = meta2rawInd(f, Nmeta)

            if iEnd < 1:
                raise ValueError(f"last index must be at least one, got {iEnd}")
            if iEnd > 100_000_000:
                raise ValueError(f"last index seems impossibly large: {iEnd}")

    return iStart, iEnd


def meta2rawInd(f, Nmetadata: int) -> int:

    if Nmetadata < 1:
        rawind = -1
    else:
        # FIXME works for .DMCdata version 1 only
        metad = np.fromfile(f, dtype=np.uint16, count=Nmetadata)
        m = pack("<2H", metad[1], metad[0])  # reorder 2 uint16
        rawind = unpack("<I", m)[0]  # always a tuple

    return rawind


def req2frame(req: list[int] | None, N: int = 0) -> npt.NDArray[np.integer]:
    """
    output has to be numpy.arange for > comparison
    """
    if req is None:
        frame = np.arange(N, dtype=np.int64)
    elif isinstance(req, int):  # the user is specifying a step size
        frame = np.arange(0, N, req, dtype=np.int64)
    elif isinstance(req, slice):
        raise TypeError(
            "slice type not allowed, pass in list or tuple with slice ordering (start, stop, step)"
        )
    elif len(req) == 1:
        frame = np.arange(0, N, req[0], dtype=np.int64)
    elif len(req) == 2:
        frame = np.arange(req[0], req[1], dtype=np.int64)
    elif len(req) == 3:
        # this is -1 because user is specifying one-based index
        frame = np.arange(req[0], req[1], req[2], dtype=np.int64) - 1  # keep -1 !
    else:  # just return all frames
        frame = np.arange(N, dtype=np.int64)

    return frame
