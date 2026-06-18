from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import numpy.typing as npt

__all__ = [
    "parse_gprmc",
    "datetime64_to_epoch",
    "frame2ut1",
    "ut12frame",
]


def parse_gprmc(nmea_file: Path | str) -> datetime:
    """
    Parse GPRMC sentence from a NMEA file and return Python datetime object.
    Returns None if the sentence is invalid or status is not 'A'.
    """
    nmea_file = Path(nmea_file)
    if not nmea_file.is_file():
        raise FileNotFoundError(nmea_file)

    with nmea_file.open("rt") as f:
        for line in f:
            if line.startswith("$GPRMC"):
                gprmc = line.strip()
                break
        else:
            raise ValueError(f"No GPRMC sentence found in {nmea_file}")

    fields = gprmc.split(",")
    if len(fields) < 10:
        raise ValueError(f"Invalid GPRMC sentence: {gprmc}")

    time_str = fields[1]  # e.g. "070005.00"
    status = fields[2]  # A = valid
    date_str = fields[9]  # e.g. "110413"

    if status != "A" or not time_str or not date_str:
        raise ValueError(f"Invalid GPRMC data: {gprmc}")

    # Parse time: HHMMSS.ss
    hh = int(time_str[0:2])
    mm = int(time_str[2:4])
    ss = float(time_str[4:])  # includes decimal seconds

    # Parse date: DDMMYY
    day = int(date_str[0:2])
    mon = int(date_str[2:4])
    year = 2000 + int(date_str[4:6])  # GPS uses 2-digit year (assumes 2000-2099)

    # GPRMC timestamps are UTC by definition.
    dt = datetime(year, mon, day, hh, mm, int(ss), int((ss % 1) * 1_000_000), tzinfo=timezone.utc)

    return dt


def datetime64_to_epoch(t: np.datetime64 | npt.NDArray[np.datetime64]) -> npt.NDArray[np.floating]:
    return t.astype("M8[ms]").astype(np.float64) / 1000.0


def frame2ut1(
    tstart: np.datetime64, kinetic_sec: float, rawind: npt.NDArray[np.integer]
) -> npt.NDArray[np.datetime64]:
    """
    Use this function for an estimate of image time.

    rawind-1 because camera is one-based indexing
    """
    if not isinstance(tstart, np.datetime64):
        tstart = np.datetime64(tstart)

    rawind = np.asarray(rawind)

    assert (
        rawind >= 1
    ).all(), "rawind should be one-based indexing since camera program started this session"

    # Compute absolute offsets then round to 100 ns ticks to avoid cumulative
    # quantization drift and stabilize float edge cases across platforms.
    dt_ns = np.rint((rawind - 1) * kinetic_sec * 1_000_000_000)
    dt_ns = ((dt_ns + 50) // 100) * 100

    return tstart + dt_ns.astype("timedelta64[ns]")


def ut12frame(treq: npt.NDArray[np.datetime64], ind: npt.NDArray[np.integer], ut1: npt.NDArray[np.datetime64]):
    """
    Given treq, output index(ces) to extract via rawDMCreader
    treq: numpy.datetime64
        requested times
    ind: zero-based file frame index corresponding to ut1, corresponding to input data file.
    ut1: numpy.datetime64
        absolute time estimate for each frame in the file, corresponding to input data file.
    We use nearest neighbor interpolation to pick a frame index for each requested time.
    """
    fReq = datetime64_to_epoch(treq)
    fUT1 = datetime64_to_epoch(ut1)

    framereq = np.rint(np.interp(fReq, fUT1, ind)).astype(np.int64)
    # discard outside time limits
    framereq = framereq[framereq >= 0]

    return framereq
