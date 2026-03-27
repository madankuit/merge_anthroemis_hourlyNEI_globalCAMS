#!/usr/bin/env bash
set -euo pipefail

IN="/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/MappedSpecies_globCAMS_conusNEI_ne0CONUSne30x8/2023_CONUSzeroOutside_temp"
OUT="${IN}/fixed_camsstyle"
DATE_TAG="c20260224"

mkdir -p "$OUT"

for f in "$IN"/*_${DATE_TAG}.nc; do
  [ -e "$f" ] || { echo "No matching files found in $IN"; exit 2; }

  bn=$(basename "$f")
  t1="${OUT}/tmp1_${bn}"
  t2="${OUT}/tmp2_${bn}"
  t3="${OUT}/tmp3_${bn}"
  of="${OUT}/${bn}"

  echo "Processing $bn"

  # 1) reorder to (time,ncol)
  ncpdq -O -a time,ncol "$f" "$t1"
  # always try rename; ignore if sum is absent
  ncrename -O -v sum,emiss "$t1" 2>/dev/null || true

  # 3) convert time to CAMS style
  python - "$t1" "$t2" <<'PY'
import sys, xarray as xr, pandas as pd
fin, fout = sys.argv[1], sys.argv[2]
ds = xr.open_dataset(fin, decode_times=True)
t = pd.to_datetime(ds["time"].values)
origin = pd.Timestamp("1950-01-01 00:00:00")
days = (t - origin) / pd.Timedelta(days=1)
ds = ds.assign_coords(time=("time", days.astype("float64")))
ds["time"].attrs["units"] = "days since 1950-01-01 00:00:00"
ds["time"].attrs["calendar"] = "standard"
ds.to_netcdf(fout, engine="netcdf4")
ds.close()
PY

  # 4) remove coord _FillValue attrs
  ncatted -O \
    -a _FillValue,ncol,d,, \
    -a _FillValue,lon,d,, \
    -a _FillValue,lat,d,, \
    -a _FillValue,area,d,, \
    -a _FillValue,rrfac,d,, \
    "$t2" "$t3"

  # 5) write as CDF5
  ncks -O -5 "$t3" "$of"

  rm -f "$t1" "$t2" "$t3"
  echo "fixed -> $of"
done

echo "Done. Output in: $OUT"
