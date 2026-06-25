# scripts/

Run-ready, **config-driven** workflow scripts. None of these hardcode machine-specific
paths — every path is read from a JSON config (`--config config/paths.json`), so the same
scripts run unchanged on any system once the config is filled in.

Run them in numbered order. Each consumes the output directory of the previous step.

| Order | Script | Purpose | Reads (config keys) | Writes (config keys) |
|-------|--------|---------|---------------------|----------------------|
| 1 | `01_merge_nei_into_cams.py` | Replace CAMS anthropogenic emissions with hourly CONUS NEI inside the CONUS ~80 km buffer, keep CAMS elsewhere, on the 0.1°×0.1° grid. | `nei_hourly_dir`, `cams_orig_dir`, `map_npz` | `merged_hourly_needs_timefix_dir` |
| 2 | `02_fix_time_coords.py` | Rewrite each merged file's hourly `time` coordinate from its filename timestamp. | `merged_hourly_needs_timefix_dir` | `merged_hourly_dir` |
| 3 | `03_combine_hourly_species_yearly.py` | Assemble hourly files into one yearly file per species, CAMS-style (monthly Zarr append → final NetCDF, via Dask). | `merged_hourly_dir` | `merged_by_species_dir` |
| 4 | `04_regrid_to_ne0conusne30x8.py` | Conservatively regrid the per-species 0.1° files to the `ne0CONUSne30x8` SE grid using the ESMF regridding package (see main README → External dependencies). | `merged_by_species_dir`, `cams_grid_file`, `serr_scrip_file`, `regridding_weights_file`, `ncar_packages_dir` | `regridded_output_dir` |

### Day-of-week time shift
When the NEI base year (`workflow.nei_actual_year`, e.g. 2022) differs from the
simulation year (`workflow.output_year`, e.g. 2023/2024), filenames are remapped to
preserve weekday/weekend patterns via `src/nei_merge/time_shift.py`.

### `run_merge_slurm.sh`
SLURM batch wrapper (Svante). Override `PYTHON_BIN` and `CONFIG_JSON` via environment
variables; defaults to `python` and `config/paths.json`.

### `ops_singularity/`
Post-processing / QA steps that finalize files for a model run (zero-outside-CONUS,
CAMS-style header fix, emissions QA). See [`ops_singularity/README.md`](ops_singularity/README.md).

---
**Usage**
```bash
cp config/paths.example.json config/paths.json   # then edit paths for your system
python3 scripts/01_merge_nei_into_cams.py --config config/paths.json
python3 scripts/02_fix_time_coords.py        --config config/paths.json
python3 scripts/03_combine_hourly_species_yearly.py --config config/paths.json
python3 scripts/04_regrid_to_ne0conusne30x8.py --config config/paths.json
```
