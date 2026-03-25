#!/usr/bin/env python3
"""
Created by Madankui Tao on Feb. 24, 2026
Rewritten (Zarr monthly append -> one yearly NetCDF per species) on Mar. 3, 2026
Optimized (parallel=True + Dask cluster, keep monthly Zarr for memory) on Mar. 7, 2026

Purpose
-------
Combine hourly merged CAMS + CONUS NEI 2022v2 emission files
(globCAMS_conusNEI2022) into one 0.1° × 0.1° global NetCDF file
per original CAMS species for the FULL YEAR.

Key optimizations over v20260303:
- Uses a Dask LocalCluster for parallel file I/O and compute
- parallel=True in open_mfdataset (files within each month read concurrently)
- Monthly Zarr append kept intentionally to avoid loading the full year in memory
- Fixed misplaced dedup: sort/dedup now runs BEFORE writing to Zarr (was after, doing nothing)

Conda Environment: filepricess
"""

import os
import sys
import shutil
import warnings

import pandas as pd
import xarray as xr
import numpy as np
from dask.distributed import Client, LocalCluster

warnings.filterwarnings(
    "ignore",
    message="The specified chunks separate the stored chunks"
)

# ===== Settings =====
DateOfModify = "_c20260224"

startDatetime = "2023-01-01T00:00:00"
endDatetime   = "2023-12-30T23:00:00"

CAMS_merged01_diri = "/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/globCAMS_conusNEI_01deg/2023_hourly_timeFixed/"
CAMS_merged01_bySpecies_diri = "/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/globCAMS_conusNEI_01deg/2023_GroupBySpecies/"
ZARR_OUT_DIR = os.path.join(CAMS_merged01_bySpecies_diri, "zarr_tmp")

WRITE_FINAL_NETCDF = True

# Tune to your machine: n_workers x threads_per_worker ~ total CPU cores available
# For I/O-heavy workloads more workers (each with fewer threads) is usually better
DASK_N_WORKERS      = 4
DASK_THREADS_WORKER = 2
DASK_MEMORY_LIMIT   = "8GB"   # per worker

DASK_CHUNKS = {"time": 24, "lat": 200, "lon": 200}

NC_COMPRESSION_LEVEL = 1
KEEP_VARS = None

# ===== Custom utilities =====
sys.path.insert(0, "/home/taoma528/Scripts/CESM_analysis/functions/")
from find_missing_files import find_missing_files_v2

# ===== Species mapping =====
CMASOrig_toNEI_dic = {
    # "acetylene": "E_C2H2",
    # "alcohols": "sum_E_CH3OH_E_C2H5OH",
    # "bc": "E_BC",
    # "benzene": "E_BENZENE",
    # "co": "E_CO",
    # "ethane": "E_C2H6",
    # "ethene": "E_C2H4",
    # "formaldehyde": "E_CH2O",
    # "isoprene": "E_ISOP",
    # "total-ketones": "sum_E_CH3COCH3_E_MEK",
    # "monoterpenes": "E_APIN",
    # "nh3": "E_NH3",
    # "nox": "sum_E_NO_NO2",
    # "oc": "E_OC",
    # "other-alkenes-and-alkynes": "E_BIGENE",
    # "propane": "E_C3H8",
    # "propene": "E_C3H6",
    "so2": "E_SO2",
    # "toluene": "E_TOLUENE",
    # "xylene": "E_XYLENE",
}

CAMSorigName_ls = list(CMASOrig_toNEI_dic.keys())
print("Species list:", CAMSorigName_ls, "\n")


# ===== Helpers =====

def preprocess_ds(ds: xr.Dataset) -> xr.Dataset:
    if KEEP_VARS is not None:
        missing = [v for v in KEEP_VARS if v not in ds.variables]
        if missing:
            raise KeyError(f"KEEP_VARS includes missing vars: {missing}. Available: {list(ds.variables)}")
        ds = ds[KEEP_VARS]
    if "time" not in ds:
        raise KeyError("Dataset has no 'time' coordinate/variable.")
    ds = ds.assign_coords(time=pd.to_datetime(ds["time"].values))
    return ds


def make_encoding_for_netcdf(ds: xr.Dataset):
    enc = {}
    for v in ds.data_vars:
        if all(d in ds[v].dims for d in ("time", "lat", "lon")):
            enc[v] = {
                "zlib": True,
                "complevel": NC_COMPRESSION_LEVEL,
                "chunksizes": (DASK_CHUNKS["time"], DASK_CHUNKS["lat"], DASK_CHUNKS["lon"]),
            }
    return enc


def parse_time_from_filename(path: str) -> pd.Timestamp:
    base = os.path.basename(path)
    stem = base[:-3]
    parts = stem.split("_")
    dt_str = parts[-2] + "_" + parts[-1]
    return pd.to_datetime(dt_str, format="conusNEI2022v2WDKadjusted_%Y-%m-%dT%H:%M:%S")


# ===== Main =====

def process_species(CAMSorigName: str):
    output_file = f"Y2023_CAMS-GLOB-ANTv6.2_conusNEI2022v2_01deg_{CAMSorigName}{DateOfModify}.nc"
    outpath = os.path.join(CAMS_merged01_bySpecies_diri, output_file)

    if os.path.exists(outpath):
        print(f"{CAMSorigName}: already exists, skipping.")
        return

    print("\n" + "=" * 90)
    print(f"Processing species: {CAMSorigName}")
    print("=" * 90)

    file_prefix = (
        "CAMS-GLOB-ANT_Glb_0.1x0.1_anthro_"
        + CAMSorigName
        + "_v6.2_monthly_conusNEI2022v2WDKadjusted"
    )
    file_suffix = ".nc"

    files_dic = find_missing_files_v2(startDatetime, endDatetime, CAMS_merged01_diri, file_prefix, file_suffix)
    missing_files = files_dic["missing_files"]
    expected_files = sorted(files_dic["expected_files"])

    if missing_files:
        print(f"STOP: missing {len(missing_files)} files. Example:", missing_files[:5])
        return

    print(f"Expected hourly files: {len(expected_files)}")

    # Parse times and group by month
    times = [parse_time_from_filename(f) for f in expected_files]
    df = pd.DataFrame({"file": expected_files, "time": times}).sort_values("time")

    start_ts = pd.to_datetime(startDatetime)
    end_ts   = pd.to_datetime(endDatetime)
    if df["time"].iloc[0] != start_ts or df["time"].iloc[-1] != end_ts:
        print("WARNING: time range from filenames does not match requested range.")
        print("  first:", df["time"].iloc[0], "expected:", start_ts)
        print("  last :", df["time"].iloc[-1], "expected:", end_ts)

    df["month"] = df["time"].dt.to_period("M")
    months = df["month"].unique().tolist()
    print("Months to process:", [str(m) for m in months])

    zarr_store = os.path.join(ZARR_OUT_DIR, f"Y2023_{CAMSorigName}{DateOfModify}.zarr")
    if os.path.exists(zarr_store):
        print("Removing existing zarr store:", zarr_store)
        shutil.rmtree(zarr_store)

    wrote_any = False
    for mi in months:
        month_files = df.loc[df["month"] == mi, "file"].tolist()
        if not month_files:
            continue

        print(f"{CAMSorigName}: {mi} -> reading {len(month_files)} files")

        ds_m = xr.open_mfdataset(
            month_files,
            engine="netcdf4",
            combine="nested",
            concat_dim="time",
            data_vars="minimal",
            coords="minimal",
            compat="override",
            parallel=True,          # <-- parallel file open via Dask (was False)
            preprocess=preprocess_ds,
            chunks=DASK_CHUNKS,
        )

        # Dedup BEFORE writing (in original this was after, so it did nothing)
        ds_m = ds_m.sortby("time")
        _, idx = np.unique(ds_m["time"].values, return_index=True)
        if len(idx) != ds_m.sizes["time"]:
            print(f"  Dropping {ds_m.sizes['time'] - len(idx)} duplicate time steps.")
            ds_m = ds_m.isel(time=np.sort(idx))

        if not wrote_any:
            ds_m.to_zarr(zarr_store, mode="w", consolidated=True)
            wrote_any = True
        else:
            ds_m.to_zarr(zarr_store, mode="a", append_dim="time", consolidated=True)

        ds_m.close()

    if not wrote_any:
        print("No data written for", CAMSorigName, "-> skipping.")
        return

    ds_all = xr.open_zarr(zarr_store, consolidated=True)

    ds_all["time"].attrs.update({"long_name": "time", "standard_name": "time"})
    ds_all["lat"].attrs.update({"long_name": "latitude", "standard_name": "latitude",
                                "units": "degrees_north", "comment": "center_of_cell"})
    ds_all["lon"].attrs.update({"long_name": "longitude", "standard_name": "longitude",
                                "units": "degrees_east", "comment": "center_of_cell"})

    if WRITE_FINAL_NETCDF:
        print("Writing final NetCDF:", outpath)
        encoding = make_encoding_for_netcdf(ds_all)
        ds_all.to_netcdf(outpath, engine="netcdf4", encoding=encoding)
        print("Saved to:", outpath)

    print("Zarr store kept at:", zarr_store)


def main():
    os.makedirs(CAMS_merged01_bySpecies_diri, exist_ok=True)
    os.makedirs(ZARR_OUT_DIR, exist_ok=True)

    # Start a local Dask cluster for the whole run
    cluster = LocalCluster(
        n_workers=DASK_N_WORKERS,
        threads_per_worker=DASK_THREADS_WORKER,
        memory_limit=DASK_MEMORY_LIMIT,
    )
    client = Client(cluster)
    print(f"Dask dashboard: {client.dashboard_link}\n")

    try:
        for CAMSorigName in CAMSorigName_ls:
            process_species(CAMSorigName)
    finally:
        client.close()
        cluster.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
