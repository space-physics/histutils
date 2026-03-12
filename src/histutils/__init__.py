"""
need to use int64 for indexing
since Numpy thru 1.11 defaults to int32 on Windows for dtype=int,
and we need int64 for large files
"""

from .utils import splitconf, write_quota, sixteen2eight
from .index import req2frame, getRawInd, meta2rawInd
from .dio import setupimgh5

__all__ = [
    "splitconf",
    "write_quota",
    "sixteen2eight",
    "req2frame",
    "getRawInd",
    "meta2rawInd",
    "setupimgh5",
]

__version__ = "1.1.0"
