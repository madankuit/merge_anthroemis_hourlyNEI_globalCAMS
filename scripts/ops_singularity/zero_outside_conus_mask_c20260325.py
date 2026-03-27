#!/usr/bin/env python3
"""
Set values outside CONUS mask to zero, preserving file structure.

Configuration is loaded from config JSON (no hardcoded server paths in script):
- workflow.output_year
- workflow.date_tag
- paths.mapped_species_dir
- paths.conus_mask_80km_file
- paths.conus_zerooutside_temp_dir

Optional config:
- ops.mask_all_ncol_vars (default: False)
- ops.species_subset (default: [])
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from pathlib import Path

import pandas as pd
import xarray as xr

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nei_merge.config import load_json_config


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=str(REPO_ROOT / "config" / "paths.json"))
    args = p.parse_args()

    cfg = load_json_config(args.config)
    workflow = cfg["workflow"]
    paths = cfg["paths"]
    ops = cfg.get("ops", {})

    year = int(workflow["output_year"])
    date_tag = workflow["date_tag"]

    in_dir = paths["mapped_species_dir"]
    out_dir = paths.get("conus_zerooutside_temp_dir")
    if not out_dir:
        out_dir = os.path.join(in_dir, f"{year}_CONUSzeroOutside_temp")
    mask_path = paths["conus_mask_80km_file"]

    mask_all_ncol_vars = bool(ops.get("mask_all_ncol_vars", False))
    species_subset = ops.get("species_subset") or None

    os.makedirs(out_dir, exist_ok=True)

    pattern = os.path.join(
        in_dir,
        f"Y{year}_CAMS-GLOB-ANTv6.2_conusNEI2022v2_ne0CONUSne30x8_*_{date_tag}.nc",
    )
    files = sorted(glob.glob(pattern))
    rx = re.compile(
        rf"Y{year}_CAMS-GLOB-ANTv6\.2_conusNEI2022v2_ne0CONUSne30x8_(?P<spc>.+?)_{date_tag}\.nc"
    )

    mask = xr.open_dataarray(mask_path).astype(bool)
    if "ncol" not in mask.dims:
        raise ValueError("Mask must have ncol dimension.")

    rows = []
    for f in files:
        bn = os.path.basename(f)
        m = rx.search(bn)
        if not m:
            continue
        sp = m.group("spc")
        if species_subset is not None and sp not in species_subset:
            continue

        out_path = os.path.join(out_dir, bn)
        try:
            ds = xr.open_dataset(f)
            if "ncol" not in ds.dims:
                raise ValueError("Input missing ncol dimension.")
            if ds.sizes["ncol"] != mask.sizes["ncol"]:
                raise ValueError(f"ncol mismatch file={ds.sizes['ncol']} mask={mask.sizes['ncol']}")

            ds_out = ds.copy(deep=True)
            for v in ds_out.data_vars:
                dims = set(ds_out[v].dims)
                do_mask = ("ncol" in dims) if mask_all_ncol_vars else (("ncol" in dims) and ("time" in dims))
                if not do_mask:
                    continue
                ds_out[v] = xr.where(mask, ds_out[v], xr.zeros_like(ds_out[v]))
                ds_out[v].attrs = ds[v].attrs.copy()

            ds_out.attrs = ds.attrs.copy()
            ds_out.to_netcdf(out_path, engine="netcdf4", unlimited_dims=["time"])
            ds.close()
            ds_out.close()
            rows.append((sp, "ok", out_path))
        except Exception as e:
            rows.append((sp, "error", str(e)))

    rep = pd.DataFrame(rows, columns=["species", "status", "note"])
    rep_path = os.path.join(out_dir, f"zero_outside_report_{year}_{date_tag}.csv")
    rep.to_csv(rep_path, index=False)
    print(rep["status"].value_counts(dropna=False))
    print(f"Report: {rep_path}")


if __name__ == "__main__":
    main()
