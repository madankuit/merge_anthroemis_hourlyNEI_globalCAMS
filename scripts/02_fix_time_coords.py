#!/usr/bin/env python3
"""Reset hourly merged-file time coordinate based on filename timestamp."""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from pathlib import Path

import numpy as np
import xarray as xr

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nei_merge.settings import load_settings


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=str(REPO_ROOT / "config" / "paths.json"))
    args = p.parse_args()

    settings = load_settings(args.config)
    paths = settings.paths

    in_dir = paths["merged_hourly_needs_timefix_dir"]
    out_dir = paths["merged_hourly_dir"]
    os.makedirs(out_dir, exist_ok=True)

    files = sorted(glob.glob(os.path.join(in_dir, "*.nc")))
    pat = re.compile(r"_(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.nc$")

    n_fix, n_skip = 0, 0
    for f in files:
        bn = os.path.basename(f)
        out_path = os.path.join(out_dir, bn)
        if os.path.exists(out_path):
            n_skip += 1
            continue

        m = pat.search(bn)
        if not m:
            print(f"Skip (no timestamp): {bn}")
            n_skip += 1
            continue

        t = np.datetime64(m.group(1)).astype("datetime64[ns]")
        ds = xr.open_dataset(f)
        ds = ds.assign_coords(time=("time", np.array([t], dtype="datetime64[ns]")))
        ds.to_netcdf(out_path)
        ds.close()
        n_fix += 1

    print(f"Done. fixed={n_fix}, skipped={n_skip}")
    print(f"Output dir: {out_dir}")


if __name__ == "__main__":
    main()
