#!/usr/bin/env python3
"""Combine hourly merged CAMS+NEI files into yearly per-species files."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from dask.distributed import Client, LocalCluster

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nei_merge.settings import load_settings
from nei_merge.find_missing_files import find_missing_files_v2

warnings.filterwarnings("ignore", message="The specified chunks separate the stored chunks")

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


def preprocess_ds(ds: xr.Dataset) -> xr.Dataset:
    if "time" not in ds:
        raise KeyError("Dataset has no time coordinate")
    return ds.assign_coords(time=pd.to_datetime(ds["time"].values))


def make_encoding(ds: xr.Dataset, chunks: dict, level: int) -> dict:
    out = {}
    for v in ds.data_vars:
        if all(d in ds[v].dims for d in ("time", "lat", "lon")):
            out[v] = {
                "zlib": True,
                "complevel": level,
                "chunksizes": (chunks["time"], chunks["lat"], chunks["lon"]),
            }
    return out


def parse_time_from_filename(path: str, merge_token: str) -> pd.Timestamp:
    base = os.path.basename(path)
    stem = base[:-3]
    parts = stem.split("_")
    dt_str = parts[-2] + "_" + parts[-1]
    return pd.to_datetime(dt_str, format=f"{merge_token}_%Y-%m-%dT%H:%M:%S")


def process_species(species: str, cfg: dict, chunks: dict, compression: int) -> None:
    workflow = cfg["workflow"]
    paths = cfg["paths"]
    date_tag = workflow["date_tag"]
    year = int(workflow["output_year"])
    cams_label = workflow.get("cams_label", "CAMS-GLOB-ANTv6.2")
    merged_label = workflow.get("merged_label", "conusNEI2022v2")
    merge_token = workflow.get("merge_token", "conusNEI2022v2WDKadjusted")

    in_dir = paths["merged_hourly_dir"]
    out_dir = paths["merged_by_species_dir"]
    zarr_dir = os.path.join(out_dir, "zarr_tmp")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(zarr_dir, exist_ok=True)

    output_file = f"Y{year}_{cams_label}_{merged_label}_01deg_{species}_{date_tag}.nc"
    outpath = os.path.join(out_dir, output_file)
    if os.path.exists(outpath):
        print(f"{species}: already exists, skipping")
        return

    file_prefix = f"CAMS-GLOB-ANT_Glb_0.1x0.1_anthro_{species}_v6.2_monthly_{merge_token}"
    files_dic = find_missing_files_v2(
        workflow["start_datetime"], workflow["end_datetime"], in_dir + "/", file_prefix, ".nc"
    )
    missing = files_dic["missing_files"]
    expected = sorted(files_dic["expected_files"])
    if missing:
        print(f"{species}: STOP missing {len(missing)} files")
        return

    times = [parse_time_from_filename(f, merge_token) for f in expected]
    df = pd.DataFrame({"file": expected, "time": times}).sort_values("time")
    df["month"] = df["time"].dt.to_period("M")

    zarr_store = os.path.join(zarr_dir, f"Y{year}_{merged_label}_{species}_{date_tag}.zarr")
    if os.path.exists(zarr_store):
        shutil.rmtree(zarr_store)

    wrote_any = False
    for month in df["month"].unique().tolist():
        month_files = df.loc[df["month"] == month, "file"].tolist()
        if not month_files:
            continue

        ds_m = xr.open_mfdataset(
            month_files,
            engine="netcdf4",
            combine="nested",
            concat_dim="time",
            data_vars="minimal",
            coords="minimal",
            compat="override",
            parallel=True,
            preprocess=preprocess_ds,
            chunks=chunks,
        )

        ds_m = ds_m.sortby("time")
        _, idx = np.unique(ds_m["time"].values, return_index=True)
        if len(idx) != ds_m.sizes["time"]:
            ds_m = ds_m.isel(time=np.sort(idx))

        if not wrote_any:
            ds_m.to_zarr(zarr_store, mode="w", consolidated=True)
            wrote_any = True
        else:
            ds_m.to_zarr(zarr_store, mode="a", append_dim="time", consolidated=True)
        ds_m.close()

    if not wrote_any:
        print(f"{species}: no data written")
        return

    ds_all = xr.open_zarr(zarr_store, consolidated=True)
    ds_all["time"].attrs.update({"long_name": "time", "standard_name": "time"})
    ds_all["lat"].attrs.update({"long_name": "latitude", "standard_name": "latitude", "units": "degrees_north"})
    ds_all["lon"].attrs.update({"long_name": "longitude", "standard_name": "longitude", "units": "degrees_east"})

    encoding = make_encoding(ds_all, chunks, compression)
    ds_all.to_netcdf(outpath, engine="netcdf4", encoding=encoding)
    ds_all.close()
    print(f"Saved: {outpath}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=str(REPO_ROOT / "config" / "paths.json"))
    args = p.parse_args()

    settings = load_settings(args.config)
    cfg = settings.raw
    combine_cfg = settings.combine
    chunks = combine_cfg.get("dask_chunks", {"time": 24, "lat": 200, "lon": 200})
    compression = int(combine_cfg.get("compression_level", 1))

    cluster = LocalCluster(
        n_workers=int(combine_cfg.get("dask_n_workers", 4)),
        threads_per_worker=int(combine_cfg.get("dask_threads_per_worker", 2)),
        memory_limit=combine_cfg.get("dask_memory_limit", "8GB"),
    )
    client = Client(cluster)
    print(client)

    try:
        subset = combine_cfg.get("species_subset") or list(CMASORIG_TO_NEI.keys())
        for sp in subset:
            process_species(sp, cfg, chunks, compression)
    finally:
        client.close()
        cluster.close()


if __name__ == "__main__":
    main()
