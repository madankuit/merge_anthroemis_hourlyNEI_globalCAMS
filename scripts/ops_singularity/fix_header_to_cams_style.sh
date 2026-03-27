#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG_JSON="${1:-${REPO_ROOT}/config/paths.json}"

IN="$(python - "$CONFIG_JSON" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
paths = cfg["paths"]
workflow = cfg["workflow"]
in_dir = paths.get("conus_zerooutside_temp_dir")
if not in_dir:
    in_dir = f"{paths['mapped_species_dir']}/{workflow['output_year']}_CONUSzeroOutside_temp"
print(in_dir)
PY
)"

OUT="$(python - "$CONFIG_JSON" <<'PY'
import json, os, sys
cfg = json.load(open(sys.argv[1]))
paths = cfg["paths"]
workflow = cfg["workflow"]
out_dir = paths.get("conus_zerooutside_fixed_dir")
if not out_dir:
    base = paths.get("conus_zerooutside_temp_dir")
    if not base:
        base = f"{paths['mapped_species_dir']}/{workflow['output_year']}_CONUSzeroOutside_temp"
    out_dir = os.path.join(base, "fixed_camsstyle")
print(out_dir)
PY
)"

DATE_TAG="$(python - "$CONFIG_JSON" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print(cfg["workflow"]["date_tag"])
PY
)"

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
