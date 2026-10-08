"""
Estimates time of DMC frames using GPS NMEA GPRMC sentences, when they exist.

We use UT1 Unix epoch time instead of datetime, since we are working with HDF5 and also need to do fast comparisons

Outputs:
--------
    UT1_unix:   double-precision float (64-bit) estimate of frame exposure START
"""

from pathlib import Path
from datetime import datetime

import numpy as np


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
            if line.startswith('$GPRMC'):
                gprmc = line.strip()
                break
        else:
            raise ValueError(f"No GPRMC sentence found in {nmea_file}")

    fields = gprmc.split(',')
    if len(fields) < 10:
        raise ValueError(f"Invalid GPRMC sentence: {gprmc}")

    time_str = fields[1]   # e.g. "070005.00"
    status   = fields[2]   # A = valid
    date_str = fields[9]   # e.g. "110413"

    if status != 'A' or not time_str or not date_str:
        raise ValueError(f"Invalid GPRMC data: {gprmc}")

    # Parse time: HHMMSS.ss
    hh = int(time_str[0:2])
    mm = int(time_str[2:4])
    ss = float(time_str[4:])          # includes decimal seconds

    # Parse date: DDMMYY
    day  = int(date_str[0:2])
    mon  = int(date_str[2:4])
    year = 2000 + int(date_str[4:6])  # GPS uses 2-digit year (assumes 2000-2099)

    # Create datetime (fractional seconds are supported)
    dt = datetime(year, mon, day, hh, mm, int(ss), int((ss % 1) * 1_000_000))

    return dt


def frame2ut1(tstart: datetime | None, kineticsec: float | None, rawind):
    """
    if you don't have GPS & fire data, you use this function for a software-only
    estimate of time. This estimate may be off by more than a minute, so think of it
    as a relative indication only. You can try verifying your absolute time with satellite
    passes in the FOV using a plate-scaled calibration and ephemeris data.

    this variable is in units of seconds since Jan 1, 1970, midnight

    rawind-1 because camera is one-based indexing
    """

    if tstart is None or kineticsec is None:
        return None

    return datetime2unix(tstart)[0] + (rawind - 1) * kineticsec


def nearest1d(xref, xq):
    """
    Return indices in xref nearest to each query value in xq.
    Ties are resolved toward the lower index.
    """

    xq = np.atleast_1d(xq).astype(float)

    right = np.searchsorted(xref, xq, side="left")
    right = np.clip(right, 0, xref.size - 1)
    left = np.maximum(right - 1, 0)

    choose_left = np.abs(xq - xref[left]) <= np.abs(xref[right] - xq)
    return np.where(choose_left, left, right).astype(np.int64)


def ut12frame(treq, ind, ut1_unix):
    """
    Given treq, output index(ces) to extract via rawDMCreader
    treq: scalar or vector of ut1_unix time (seconds since Jan 1, 1970)
    ind: zero-based frame index corresponding to ut1_unix, corresponding to input data file.
    Returns None when treq is None, allowing the caller to select frames by index.
    """

    if treq is None:
        return None

    treq = np.atleast_1d(treq)
    match treq.size:
        case 1:
            treq = datetime2unix(treq[0])
        case 2:
            # range of requested times
            i = (ut1_unix >= datetime2unix(treq[0])) & (ut1_unix < datetime2unix(treq[1]))
            treq = ut1_unix[i]
        case _:
            # vector of requested times
            treq = datetime2unix(treq)
    # Pick the nearest timestamp with searchsorted and map to its frame index.
    in_range = (treq >= ut1_unix[0]) & (treq <= ut1_unix[-1])
    treq = treq[in_range]

    nearest = nearest1d(ut1_unix, treq)
    framereq = ind[nearest]

    return framereq


def datetime2unix(T: datetime):
    """
    converts datetime to UT1 unix epoch time

    Returns
    -------

    numpy.ndarray of float, shape (N,) where N is the number of input datetimes
        UT1 unix epoch time in seconds since Jan 1, 1970 midnight
    """

    Ta = np.atleast_1d(T)  # type: ignore [call-overload]
    # datetime isn't part of npt.ArrayLike due to https://github.com/numpy/numpy/pull/31479

    ut1_unix = np.empty(Ta.shape, dtype=float)
    for i, t in enumerate(Ta):
        match t:
            case datetime():
                pass
            case np.datetime64():
                t = t.astype("datetime64[ms]").astype(datetime)
            case str():
                t = datetime.fromisoformat(t)
            case float():
                return Ta
            case int():
                return Ta.astype(float)
            case _:
                raise TypeError("Expecting datetime or parsable date string")

        # ut1 seconds since unix epoch, need [] for error case
        ut1_unix[i] = t.timestamp()

    return ut1_unix


def firetime(tstart, Tfire):
    """Highly accurate sub-millisecond absolute timing based on GPSDO 1PPS and camera fire feedback.
    Right now we have some piecemeal methods to do this, and it's time to make it industrial strength
    code.

    """
    raise NotImplementedError("Yes this is a priority, would you like to volunteer?")
