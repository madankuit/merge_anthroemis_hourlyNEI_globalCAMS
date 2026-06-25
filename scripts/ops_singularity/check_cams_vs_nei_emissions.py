#!/usr/bin/env python3
"""Condensed QA checks for NEI2022v2 + CAMS v6.2 mapped-species outputs.

Checks:
1) species intersection between mapped hourly files and CAMS monthly references
2) monthly mean difference stats for one species inside CONUS 80km mask

Usage:
  python3 scripts/ops_singularity/check_cams_vs_nei_emissions.py --config config/paths.json --species NO --month 2023-07
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import xarray as xr


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nei_merge.config import load_json_config  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Condensed NEI/CAMS QA checks")
    p.add_argument("--config", default="config/paths.json", help="Path to JSON config")
    p.add_argument("--species", default="NO", help="Species to test (e.g., NO, CO, SO2)")
    p.add_argument("--month", default="2023-07", help="Month for monthly-mean diff (YYYY-MM)")
    return p.parse_args()


def species_from_files(folder: Path, rx: re.Pattern[str]) -> list[str]:
    out: list[str] = []
    for f in sorted(folder.glob("*.nc")):
        m = rx.search(f.name)
        if m:
            out.append(m.group("spc"))
    return sorted(set(out))


def main() -> None:
    args = parse_args()
    cfg = load_json_config(args.config)
    paths = cfg["paths"]
    workflow = cfg["workflow"]

    date_tag = workflow["date_tag"]
    output_year = int(workflow["output_year"])
    cams_label = workflow.get("cams_label", "CAMS-GLOB-ANTv6.2")
    merged_label = workflow.get("merged_label", "conusNEI2022v2")
    grid_label = workflow.get("target_grid_label", "ne0CONUSne30x8")
    mapped_stem = f"Y{output_year}_{cams_label}_{merged_label}_{grid_label}"

    mapped_dir = Path(paths["mapped_species_dir"])
    cams_dir = Path(paths["cams_ne0conus_monthly_dir"])
    mask_file = Path(paths["conus_mask_80km_file"])

    rx_nei = re.compile(rf"{re.escape(mapped_stem)}_(?P<spc>.+?)_{re.escape(date_tag)}\.nc$")
    rx_cams = re.compile(r"CAMS-GLOB-ANT_ne0conus30x8_(?P<spc>.+?)_v6\.2_monthly\.nc$")

    mapped_species = species_from_files(mapped_dir, rx_nei)
    cams_species = species_from_files(cams_dir, rx_cams)
    common_species = sorted(set(mapped_species).intersection(cams_species))
    only_mapped = sorted(set(mapped_species) - set(cams_species))
    only_cams = sorted(set(cams_species) - set(mapped_species))

    print("=== Species Match ===")
    print("Mapped count:", len(mapped_species))
    print("CAMS count  :", len(cams_species))
    print("Common count:", len(common_species))
    if only_mapped:
        print("Only mapped:", only_mapped)
    if only_cams:
        print("Only CAMS  :", only_cams)

    spc = args.species
    mapped_file = mapped_dir / f"{mapped_stem}_{spc}_{date_tag}.nc"
    cams_file = cams_dir / f"CAMS-GLOB-ANT_ne0conus30x8_{spc}_v6.2_monthly.nc"

    if not mapped_file.exists():
        raise FileNotFoundError(f"Mapped file not found: {mapped_file}")
    if not cams_file.exists():
        raise FileNotFoundError(f"CAMS file not found: {cams_file}")

    ds_nei = xr.open_dataset(mapped_file)
    ds_cams = xr.open_dataset(cams_file)
    var_nei = "emiss" if "emiss" in ds_nei.data_vars else "sum"
    var_cams = "emiss" if "emiss" in ds_cams.data_vars else "sum"

    nei_da = ds_nei[var_nei]
    cams_da = ds_cams[var_cams]

    mask_nei = nei_da.time.dt.strftime("%Y-%m") == args.month
    mask_cams = cams_da.time.dt.strftime("%Y-%m") == args.month

    if int(mask_nei.sum()) == 0:
        raise ValueError(f"No NEI timesteps found for month {args.month}")
    if int(mask_cams.sum()) == 0:
        raise ValueError(f"No CAMS timesteps found for month {args.month}")

    nei_mean = nei_da.sel(time=mask_nei).mean(dim="time")
    cams_mean = cams_da.sel(time=mask_cams).mean(dim="time")

    mask_da = xr.open_dataarray(mask_file)
    diff_conus = xr.where(mask_da, nei_mean - cams_mean, 0.0)

    print("\n=== Monthly Diff Stats (inside CONUS mask) ===")
    print("Species:", spc, "Month:", args.month)
    print("NEI ntime in month :", int(mask_nei.sum()))
    print("CAMS ntime in month:", int(mask_cams.sum()))
    print("min/max:", float(diff_conus.where(mask_da).min()), float(diff_conus.where(mask_da).max()))
    print("mean abs:", float(np.abs(diff_conus.where(mask_da)).mean()))
    print("nonzero count:", int(((diff_conus.where(mask_da) != 0) & mask_da).sum()))

    ds_nei.close()
    ds_cams.close()


if __name__ == "__main__":
    main()
