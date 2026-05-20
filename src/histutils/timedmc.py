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


def frame2ut1(tstart, kineticsec, rawind):
    """
    if you don't have GPS & fire data, you use this function for a software-only
    estimate of time. This estimate may be off by more than a minute, so think of it
    as a relative indication only. You can try verifying your absolute time with satellite
    passes in the FOV using a plate-scaled calibration and ephemeris data.

    this variable is in units of seconds since Jan 1, 1970, midnight

    rawind-1 because camera is one-based indexing
    """

    return datetime2unix(tstart)[0] + (rawind - 1) * kineticsec


def ut12frame(treq, ind, ut1_unix):
    """
    Given treq, output index(ces) to extract via rawDMCreader
    treq: scalar or vector of ut1_unix time (seconds since Jan 1, 1970)
    ind: zero-based frame index corresponding to ut1_unix, corresponding to input data file.
    """
    if treq is None:  # have to do this since interp1 will return last index otherwise
        return None

    treq = np.atleast_1d(treq)
    # %% handle human specified string scalar case
    if treq.size == 1:
        treq = datetime2unix(treq[0])
    # %% handle time range case
    elif treq.size == 2:
        tstartreq = datetime2unix(treq[0])
        tendreq = datetime2unix(treq[1])
        treq = ut1_unix[(ut1_unix > tstartreq) & (ut1_unix < tendreq)]
    else:  # otherwise, it's a vector of requested values
        treq = datetime2unix(treq)
    # %% get indices
    """
    We use nearest neighbor interpolation to pick a frame index for each requested time.
    """
    framereq = np.rint(np.interp(treq, ut1_unix, ind)).astype(np.int64)
    framereq = framereq[framereq >= 0]  # discard outside time limits

    return framereq


def datetime2unix(T):
    """
    converts datetime to UT1 unix epoch time

    Returns
    -------

    numpy.ndarray of float, shape (N,) where N is the number of input datetimes
        UT1 unix epoch time in seconds since Jan 1, 1970 midnight
    """
    T = np.atleast_1d(T)

    ut1_unix = np.empty(T.shape, dtype=float)
    for i, t in enumerate(T):
        match t:
            case datetime():
                pass
            case np.datetime64():
                t = t.astype("datetime64[ms]").astype(datetime)
            case str():
                t = datetime.fromisoformat(t)
            case float():
                return T
            case int():
                return T.astype(float)
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
