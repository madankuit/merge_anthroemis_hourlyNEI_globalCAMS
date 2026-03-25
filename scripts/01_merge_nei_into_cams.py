#!/usr/bin/env python3
"""Merge hourly CONUS NEI emissions into global CAMS files.

All machine-specific paths are loaded from an external JSON config.
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nei_merge.config import load_json_config, require_keys
from nei_merge.time_shift import NEIfileDatetime_shift_BACKWARD, NEIfileDatetime_shift_BYweekofday


CMASORIG_TO_NEI = {
    "acetylene": "E_C2H2",
    "alcohols": "sum_E_CH3OH_E_C2H5OH",
    "bc": "E_BC",
    "benzene": "E_BENZENE",
    "co": "E_CO",
    "ethane": "E_C2H6",
    "ethene": "E_C2H4",
    "formaldehyde": "E_CH2O",
    "isoprene": "E_ISOP",
    "total-ketones": "sum_E_CH3COCH3_E_MEK",
    "monoterpenes": "E_APIN",
    "nh3": "E_NH3",
    "nox": "sum_E_NO_NO2",
    "oc": "E_OC",
    "other-alkenes-and-alkynes": "E_BIGENE",
    "propane": "E_C3H8",
    "propene": "E_C3H6",
    "so2": "E_SO2",
    "toluene": "E_TOLUENE",
    "xylene": "E_XYLENE",
}


def convert_molkm2hr_to_kgm2s(vals_molkm2hr: np.ndarray, molecular_weight: float) -> np.ndarray:
    return vals_molkm2hr * (1.0 / 3600.0) * (1.0 / 1e6) * (molecular_weight * 1e-3)


def convert_ugm2s_to_kgm2s(vals_ugm2s: np.ndarray) -> np.ndarray:
    return vals_ugm2s * 1e-9


def extract_date_and_time(filename: str) -> datetime:
    return datetime.strptime(filename[13:], "%Y-%m-%d_%H:%M:%S")


def read_nei_files(start_datetime_u: str, end_datetime_u: str, nei_actual_year: int, nei_dir: str) -> list[str]:
    nei_start = NEIfileDatetime_shift_BACKWARD(start_datetime_u, nei_actual_year)
    nei_end = NEIfileDatetime_shift_BACKWARD(end_datetime_u, nei_actual_year)

    start_dt = datetime.strptime(nei_start, "%Y-%m-%d_%H:%M:%S")
    end_dt = datetime.strptime(nei_end, "%Y-%m-%d_%H:%M:%S")

    selected = []
    for file_name in os.listdir(nei_dir):
        if not file_name.startswith("wrfchemi_d01_"):
            continue
        file_date = datetime.strptime(file_name[13:], "%Y-%m-%d_%H:%M:%S")
        if start_dt <= file_date <= end_dt:
            selected.append(file_name)

    selected = sorted(selected, key=extract_date_and_time)
    print(f"{len(selected)} NEI files within requested time range")
    return selected


def get_nei_species_da(nei_ds: xr.Dataset, cams_species: str) -> xr.DataArray:
    nei_name = CMASORIG_TO_NEI[cams_species]
    tokens = nei_name.split("_")
    if tokens[0] != "sum":
        return nei_ds[nei_name]

    species_list = [t for t in tokens if t not in ["sum", "E"]]
    var1 = "E_" + species_list[0]
    var2 = "E_" + species_list[1]
    summed = nei_ds[var1] + nei_ds[var2]
    da = xr.DataArray(summed, coords=nei_ds[var1].coords, attrs=nei_ds[var1].attrs)
    da.attrs["description"] = f"NEI emissions summed for {var1} and {var2}"
    return da


def process_one(cams_species: str, nei_file: str, cfg: dict, map_data: dict[str, np.ndarray]) -> None:
    workflow = cfg["workflow"]
    paths = cfg["paths"]
    output_year = int(workflow["output_year"])
    merge_token = workflow.get("merge_token", "conusNEI2022v2WDKadjusted")
    inventory_name = workflow.get("inventory_name", "NEI")

    search_str = f"_{cams_species}_"
    cams_matches = glob.glob(os.path.join(paths["cams_orig_dir"], f"*{search_str}*"))
    if not cams_matches:
        raise FileNotFoundError(f"No CAMS monthly file found for species: {cams_species}")

    cams_file = cams_matches[0]
    shifted_name = NEIfileDatetime_shift_BYweekofday(nei_file, output_year)

    dt_str = shifted_name[-19:]
    dt64 = np.datetime64(dt_str[:10] + "T" + dt_str[11:] + ".000000000")
    month_key = shifted_name[13:20]

    out_dir = paths["merged_hourly_dir"]
    os.makedirs(out_dir, exist_ok=True)

    fn_base, ext = os.path.splitext(os.path.basename(cams_file))
    out_name = f"{fn_base}_{merge_token}_{str(dt64)[:19]}{ext}"
    out_path = os.path.join(out_dir, out_name)
    if os.path.exists(out_path):
        print(f"Skip existing: {out_name}")
        return

    cams_ds = xr.open_dataset(cams_file)
    monthi = cams_ds.sel(time=pd.DatetimeIndex(cams_ds["time"].values).strftime("%Y-%m") == month_key)

    nei_ds = xr.open_dataset(os.path.join(paths["nei_hourly_dir"], nei_file))
    nei_da = get_nei_species_da(nei_ds, cams_species)

    orig_unit = nei_da.units
    molecular_weight = int(monthi["sum"].molecular_weight)
    if orig_unit == "ug m^-2 s^-1":
        vals = convert_ugm2s_to_kgm2s(nei_da.values)
    elif orig_unit == "mol km^-2 hr^-1":
        vals = convert_molkm2hr_to_kgm2s(nei_da.values, molecular_weight)
    else:
        raise ValueError(f"Unsupported NEI unit for {cams_species}: {orig_unit}")

    checked = xr.DataArray(vals, dims=nei_da.dims, coords=nei_da.coords, attrs=nei_da.attrs.copy())
    checked.name = nei_da.name
    time_dim = "Time" if "Time" in checked.dims else "time"

    nei2d = checked.sum(dim="emissions_zdim_stag").isel({time_dim: 0}).values
    nei_on_cams = nei2d[map_data["nei_sn"], map_data["nei_we"]]
    replace_ok = (nei_on_cams > 1e-21) & map_data["dist_ok"]

    merged = monthi.copy(deep=True)
    merged["sum"].values[0, map_data["cams_ii"][replace_ok], map_data["cams_jj"][replace_ok]] = nei_on_cams[replace_ok]

    merged.attrs["NEI_merge_note"] = (
        "Merged CAMS with NEI inside buffered CONUS using nearest-neighbor map "
        f"({paths['map_npz']}); dist<={cfg['merge']['distance_cutoff_deg']} deg."
    )

    t = np.datetime64(str(dt64).replace(".000000000", ""))
    merged = merged.assign_coords(time=("time", np.array([t], dtype="datetime64[ns]")))

    long_name = merged["sum"].attrs.get("long_name", "sum")
    merged["sum"].attrs["long_name"] = (
        f"{long_name} (merged Y{output_year} global CAMS with CONUS {inventory_name}, weekday/weekend adjusted)"
    )

    merged.to_netcdf(out_path)
    cams_ds.close()
    nei_ds.close()
    print(f"Saved: {out_path}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=str(REPO_ROOT / "config" / "paths.json"))
    args = p.parse_args()

    cfg = load_json_config(args.config)
    require_keys(cfg, ["workflow", "paths", "merge"], "root config")

    workflow = cfg["workflow"]
    paths = cfg["paths"]
    require_keys(
        workflow,
        ["start_datetime", "end_datetime", "nei_actual_year", "output_year"],
        "workflow",
    )
    require_keys(paths, ["nei_hourly_dir", "cams_orig_dir", "merged_hourly_dir", "map_npz"], "paths")

    start_u = workflow["start_datetime"].replace("T", "_")
    end_u = workflow["end_datetime"].replace("T", "_")
    nei_actual_year = int(workflow["nei_actual_year"])

    m = np.load(paths["map_npz"], allow_pickle=True)
    dist_cut = float(cfg["merge"].get("distance_cutoff_deg", 0.125))
    map_data = {
        "cams_ii": m["cams_ii"],
        "cams_jj": m["cams_jj"],
        "nei_sn": m["nei_sn"],
        "nei_we": m["nei_we"],
        "dist_ok": m["dist_deg"] <= dist_cut,
    }

    nei_files = read_nei_files(start_u, end_u, nei_actual_year, paths["nei_hourly_dir"])
    species_subset = cfg["merge"].get("species_subset") or list(CMASORIG_TO_NEI.keys())

    for nei_file in nei_files:
        for cams_species in species_subset:
            process_one(cams_species, nei_file, cfg, map_data)


if __name__ == "__main__":
    main()
