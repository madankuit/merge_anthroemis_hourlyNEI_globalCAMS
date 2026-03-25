#!/usr/bin/env python3
"""Regrid combined species files from 0.1x0.1 grid to ne0CONUSne30x8."""

from __future__ import annotations

import argparse
import fnmatch
import glob
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import xarray as xr

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nei_merge.config import load_json_config, require_keys


def get_spc_and_spcfiles(file_list: Iterable[str]) -> Tuple[List[str], Dict[str, str]]:
    pat = re.compile(r"_01deg_(?P<spc>.+?)_c\d{8}\.nc$")
    spc_to_file: Dict[str, str] = {}

    for fp in file_list:
        bn = os.path.basename(fp)
        m = pat.search(bn)
        if not m:
            continue
        spc = m.group("spc")
        if spc in spc_to_file:
            if os.path.getmtime(fp) > os.path.getmtime(spc_to_file[spc]):
                spc_to_file[spc] = fp
        else:
            spc_to_file[spc] = fp

    return sorted(spc_to_file.keys()), spc_to_file


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=str(REPO_ROOT / "config" / "paths.json"))
    args = p.parse_args()

    cfg = load_json_config(args.config)
    require_keys(cfg, ["workflow", "paths", "regrid"], "root config")

    paths = cfg["paths"]
    workflow = cfg["workflow"]
    require_keys(
        paths,
        [
            "merged_by_species_dir",
            "regridded_output_dir",
            "cams_grid_file",
            "serr_scrip_file",
            "regridding_weights_file",
            "ncar_packages_dir",
        ],
        "paths",
    )

    sys.path.insert(0, paths["ncar_packages_dir"])
    from dsj.analysis.Regridding_ESMF import Regridding

    date_tag = workflow["date_tag"]
    year = int(workflow["output_year"])

    file_dir = paths["merged_by_species_dir"]
    pattern = f"Y{year}_CAMS-GLOB-ANTv6.2_conusNEI2022v2_01deg_*_{date_tag}.nc"
    file_list = [
        f for f in glob.glob(os.path.join(file_dir, pattern)) if fnmatch.fnmatch(os.path.basename(f), pattern)
    ]

    species, species_files = get_spc_and_spcfiles(file_list)
    subset = cfg["regrid"].get("species_subset")
    if subset:
        species = [s for s in species if s in subset]

    os.makedirs(paths["regridded_output_dir"], exist_ok=True)
    dst_fmt = os.path.join(
        paths["regridded_output_dir"],
        f"Y{year}_CAMS-GLOB-ANTv6.2_conusNEI2022v2_ne0CONUSne30x8_SPC_{date_tag}.nc",
    )

    for sp in species:
        dst_file = dst_fmt.replace("SPC", sp)
        if os.path.exists(dst_file):
            print(f"{sp} already processed")
            continue

        print(f"Regridding: {sp}")
        ds_emis = xr.open_dataset(species_files[sp])
        Regridding(
            ds_emis,
            src_grid_file=paths["cams_grid_file"],
            dst_grid_file=paths["serr_scrip_file"],
            wgt_file=paths["regridding_weights_file"],
            method="Conserve",
            fields=[],
            dst_file=dst_file,
            save_wgt_file=False,
            save_results=True,
            check_results=False,
            check_timings=True,
            creation_date=False,
            nc_file_format="NETCDF4",
        )

        src_time = np.array(ds_emis["time"].values, dtype="datetime64[ns]")
        ds_out = xr.open_dataset(dst_file)
        if "time" not in ds_out.dims:
            raise ValueError(f"[{sp}] dst file has no time dimension")
        if ds_out.sizes["time"] != len(src_time):
            raise ValueError(f"[{sp}] time size mismatch: dst={ds_out.sizes['time']} src={len(src_time)}")

        ds_out = ds_out.assign_coords(time=("time", src_time))
        ds_out.attrs["time_fix_note"] = "Time coordinate replaced to match source hourly species file."

        tmp = dst_file + ".tmp"
        ds_out.to_netcdf(tmp)
        ds_out.close()
        ds_emis.close()
        os.replace(tmp, dst_file)
        print(f"Saved: {dst_file}")


if __name__ == "__main__":
    main()
