#!/usr/bin/env python3
"""
Set values outside CONUS mask to zero, preserving file structure.

Default behavior:
- only mask variables with dims containing BOTH ("time", "ncol")
- coordinates unchanged
- metadata preserved
"""

import os
import re
import glob
import numpy as np
import pandas as pd
import xarray as xr

IN_DIR = "/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/MappedSpecies_globCAMS_conusNEI_ne0CONUSne30x8/2023/"
OUT_DIR = "/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/MappedSpecies_globCAMS_conusNEI_ne0CONUSne30x8/2023_CONUSzeroOutside_temp/"
MASK_PATH = "/home/taoma528/Scripts/CESM_analysis/functions/ne0CONUSne30x8_np4_CONUSlandMaskedFalse_80kmBuffer.nc"

YEAR = 2023
DATE_TAG = "c20260224"

# If True, mask any data_var containing ncol (including lon/lat/area/etc).
# Usually keep this False.
MASK_ALL_NCOL_VARS = False

SPECIES_SUBSET = ["so4_a1_ene_vertical"]  # test one species first
# SPECIES_SUBSET = None

os.makedirs(OUT_DIR, exist_ok=True)

pattern = os.path.join(
    IN_DIR,
    f"Y{YEAR}_CAMS-GLOB-ANTv6.2_conusNEI2022v2_ne0CONUSne30x8_*_{DATE_TAG}.nc"
)
files = sorted(glob.glob(pattern))
rx = re.compile(
    rf"Y{YEAR}_CAMS-GLOB-ANTv6\.2_conusNEI2022v2_ne0CONUSne30x8_(?P<spc>.+?)_{DATE_TAG}\.nc"
)

mask = xr.open_dataarray(MASK_PATH).astype(bool)
if "ncol" not in mask.dims:
    raise ValueError("Mask must have ncol dimension.")

rows = []

for f in files:
    bn = os.path.basename(f)
    m = rx.search(bn)
    if not m:
        continue
    sp = m.group("spc")
    if SPECIES_SUBSET is not None and sp not in SPECIES_SUBSET:
        continue

    out_path = os.path.join(OUT_DIR, bn)

    try:
        ds = xr.open_dataset(f)
        if "ncol" not in ds.dims:
            raise ValueError("Input missing ncol dimension.")
        if ds.sizes["ncol"] != mask.sizes["ncol"]:
            raise ValueError(f"ncol mismatch file={ds.sizes['ncol']} mask={mask.sizes['ncol']}")

        ds_out = ds.copy(deep=True)

        for v in ds_out.data_vars:
            dims = set(ds_out[v].dims)

            if MASK_ALL_NCOL_VARS:
                do_mask = "ncol" in dims
            else:
                do_mask = ("ncol" in dims) and ("time" in dims)

            if not do_mask:
                continue

            zeros = xr.zeros_like(ds_out[v])
            ds_out[v] = xr.where(mask, ds_out[v], zeros)
            ds_out[v].attrs = ds[v].attrs.copy()

        ds_out.attrs = ds.attrs.copy()
        ds_out.to_netcdf(out_path, engine="netcdf4", unlimited_dims=["time"])
        ds.close()
        ds_out.close()

        rows.append((sp, "ok", out_path))
    except Exception as e:
        rows.append((sp, "error", str(e)))

rep = pd.DataFrame(rows, columns=["species", "status", "note"])
rep_path = os.path.join(OUT_DIR, f"zero_outside_report_{YEAR}_{DATE_TAG}.csv")
rep.to_csv(rep_path, index=False)

print(rep["status"].value_counts(dropna=False))
print(f"Report: {rep_path}")
