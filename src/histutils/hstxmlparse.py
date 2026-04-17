#!/usr/bin/env python
"""
retrieve parameters from HiST .DMCdata experiment .xml files
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any


def xmlparam(fn: Path) -> Dict[str, Any]:
    """
    reads necessary camera parameters into dict

    * kinetic rate (1/frame rate) seconds
    * resolution pixels
    * binning pixels

    Parameters
    ----------

    fn : pathlib.Path
        filename of XML file corresponding to .DMCdata file

    Returns
    -------

    params : dict
        camera parameters of interest
    """
    tree = ET.parse(fn)

    root = tree.getroot()
    children = list(root)

    data = children[1]

    params: Dict[str, Any] = {}

    diter = data.iter()
    for el in diter:
        txt = el.text
        match txt:
            case "Binning (H x V)":
                if txt := next(diter).text:
                    params["binning"] = int(txt)
            case "ROI H Pixels":
                if txt := next(diter).text:
                    params["horizpixels"] = int(txt)
            case "ROI V Pixels":
                if txt := next(diter).text:
                    params["vertpixels"] = int(txt)
            case "Freq":
                if txt := next(diter).text:
                    params["pulsefreq"] = float(txt)
                    params["kineticrate"] = 1 / params["pulsefreq"]
            case _:
                pass

    return params
