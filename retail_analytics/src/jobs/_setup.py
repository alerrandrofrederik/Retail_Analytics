"""Shared start of the job scripts: the package in src/ on the path, the arguments, and the lake folders."""

import argparse
import sys
from pathlib import Path

try:
    HERE = Path(__file__).resolve().parent
except NameError:  # some runners execute the file without __file__
    HERE = Path(sys.argv[0]).resolve().parent
sys.path.insert(0, str(HERE.parent))


def arguments(*extra):
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="lh_retail_analytics")
    for name in extra:
        parser.add_argument(f"--{name}", required=True)
    return parser.parse_args()


def lake(catalog, layer, volume="files"):
    """The folder of a layer in its Unity Catalog volume."""
    return Path(f"/Volumes/{catalog}/{layer}/{volume}")
