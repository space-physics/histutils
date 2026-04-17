#!/usr/bin/env python3
"""
demos reading HiST camera parameters from XML file
"""

from histutils.hstxmlparse import xmlparam
from argparse import ArgumentParser


p = ArgumentParser()
p.add_argument("fn", help="xml filename to parse")
args = p.parse_args()

params = xmlparam(args.fn)

print(params)
