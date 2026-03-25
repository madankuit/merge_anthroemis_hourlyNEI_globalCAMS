# Reset the NetCDF time coordinate of hourly merged CAMS+CONUS NEI files to match their filename timestamps, enabling correct multi-file time concatenation.

import os, re, glob
import numpy as np
import xarray as xr

in_dir  = "/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/globCAMS_conusNEI_01deg/2023_hourly_NeedsCorrection/"
out_dir = "/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/globCAMS_conusNEI_01deg/2023_hourly_timeFixed/"

# create the out_dir if not there yet
# os.makedirs(out_dir, exist_ok=True)

files = sorted(glob.glob(os.path.join(in_dir, "*.nc")))

# matches ..._2023-01-31T10:00:00.nc
pat = re.compile(r"_(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.nc$")

n_fix, n_skip = 0, 0

for f in files:
    bn = os.path.basename(f)
    out_path = os.path.join(out_dir, bn)
    if os.path.exists(out_path):
        print("Skip since processed")
        n_skip += 1
    else:
        m = pat.search(bn)
        if not m:
            print("Skip (no time found):", bn)
            n_skip += 1
            continue

        # parse time from filename
        t = np.datetime64(m.group(1)).astype("datetime64[ns]")

        ds = xr.open_dataset(f)

        # force time coordinate to match filename (keep time dimension length-1)
        ds = ds.assign_coords(time=("time", np.array([t], dtype="datetime64[ns]")))

        ds.to_netcdf(out_path)
        ds.close()

        n_fix += 1

print(f"Done. fixed={n_fix}, skipped={n_skip}")
print("Output dir:", out_dir)