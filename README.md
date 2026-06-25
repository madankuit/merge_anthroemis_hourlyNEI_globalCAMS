# merge_anthroemis_hourlyNEI_globalCAMS

Process hourly NEI emissions and merge into CAMS anthropogenic emissions, then prepare run-ready files on `ne0CONUSne30x8`.

## Scope

Current documented workflow is for:

- NEI: `NEI2022v2`
- CAMS: `CAMS-GLOB-ANT v6.2`
- Target year: `2023`
- Grid: `ne0CONUSne30x8`

> **Note on years.** The hourly NEI inventory is `NEI2022v2` (base year 2022). To run
> other simulation years (e.g. 2023, 2024) the NEI filenames are remapped to preserve
> day-of-week (weekday/weekend) patterns — see `src/nei_merge/time_shift.py` and
> `workflow.nei_actual_year` / `workflow.output_year` in the config.

## Repository Layout

Every folder has its own README with details. Quick map:

| Folder | What's in it |
|--------|--------------|
| [`scripts/`](scripts/README.md) | Run-ready, config-driven workflow steps `01`–`04` + SLURM wrapper. |
| [`scripts/ops_singularity/`](scripts/ops_singularity/README.md) | Post-processing & QA (zero-outside-CONUS, CAMS-style header fix, QA script). |
| [`src/nei_merge/`](src/nei_merge/README.md) | Shared helper package: config loader, settings schema, day-of-week time shift, missing-file finder. |
| [`config/`](config/README.md) | All machine-specific paths/settings (templates + the author's real-path reference). |
| [`notebooks/`](notebooks/README.md) | Interactive QA / diagnostics. |
| [`originals/`](originals/README.md) | Unmodified original scripts, kept verbatim for provenance (still contain hardcoded paths — do not run as-is). |
| [`docs/`](docs/README.md) | Project inventory mapping original scripts → cleaned repo. |

## External dependencies

- **Python environment** — see `requirements.txt` (xarray, numpy, pandas, dask, netCDF4, etc.).
- **ESMF conservative regridding (Step 5 only).** `scripts/04_regrid_to_ne0conusne30x8.py`
  imports a regridding utility (`Regridding_ESMF`) from an **external NCAR package by
  Duseong Jo (NCAR/ACOM)**, located via the `ncar_packages_dir` config key. This package
  is **not redistributed here.** To run Step 5 you need either that package or an
  equivalent ESMF/`esmpy` regridder. An M. Tao–revised copy of the same engine
  (`functions/Regridding_ESMF_MTv1.py`) is available in the companion repository
  [`MUSICAv0-workflows`](https://github.com/madankuit/MUSICAv0-workflows). Steps 1–4 do
  not need it. (If you regrid to your own grid, you can substitute your own regridder at
  this step.)

## Workflow (Numbered)

### Step 1: Preprocess NEI to 0.1° CONUS grid

Use `epa_anthro_emis` (T1 mechanism) to generate hourly NEI files on CONUS 0.1° x 0.1°.

### Step 2: Merge NEI with CAMS on 0.1° grid

Replace CAMS with NEI inside CONUS (~80 km coastal buffer), keep CAMS outside.

- Repo script: `scripts/01_merge_nei_into_cams.py`

### Step 3: Fix hourly time coordinates

Correct hourly time metadata after merge.

- Repo script: `scripts/02_fix_time_coords.py`

### Step 4: Combine hourly files by species (yearly)

Build one yearly file per species in CAMS-style structure.

- Repo script: `scripts/03_combine_hourly_species_yearly.py`

### Step 5: Regrid to ne0CONUSne30x8

Regrid merged files from 0.1° grid to model grid.

- Repo script: `scripts/04_regrid_to_ne0conusne30x8.py`

### Step 6: Species mapping

Map species to CAM-chem mechanism (TS1/T1-compatible mapping used in this workflow).

- Mapping template: `config/species_mapping_template.dat`
- Historical mapping notebook reference: `Species_Mapping_NEI2022v2_CAMSv6.2_ne0CONUSne30x8.ipynb`

### Step 7: Zero emissions outside CONUS mask

Set values to zero outside CONUS 80 km buffer while keeping file structure.

- Script: `scripts/ops_singularity/zero_outside_conus_mask_c20260325.py`
- Run:

```bash
python3 scripts/ops_singularity/zero_outside_conus_mask_c20260325.py --config config/paths.json
```

### Step 8: Fix NetCDF header/format to CAMS style + QA

Normalize format for run compatibility (dimension order, variable naming, time encoding, CDF5), then validate with notebook checks.

- Script: `scripts/ops_singularity/fix_header_to_cams_style.sh`
- Condensed QA script: `scripts/ops_singularity/check_cams_vs_nei_emissions.py`
- Notebook: `notebooks/NEI2022v2_CAMSv6.2.ipynb`
- Run:

```bash
bash scripts/ops_singularity/fix_header_to_cams_style.sh config/paths.json
python3 scripts/ops_singularity/check_cams_vs_nei_emissions.py --config config/paths.json --species NO --month 2023-07
```

## Configuration

All runtime paths live in one external file — the active scripts/notebooks contain
**no hardcoded server paths**. See [`config/README.md`](config/README.md) for the full
schema. The three config files:

- `config/paths.example.json` — **template for new users.** Placeholder paths; copy to
  `config/paths.json` and edit for your system.
- `config/paths.json` — what the scripts actually read (`--config config/paths.json`).
  Gitignored; local to each machine.
- `config/paths.svante.json` — the author's real Svante paths, tracked so they stay in
  sync between machines. On Svante just `cp config/paths.svante.json config/paths.json`.

Key path entries used by the final steps:

- `paths.mapped_species_dir`
- `paths.cams_ne0conus_monthly_dir`
- `paths.conus_mask_80km_file`
- `paths.conus_zerooutside_temp_dir`
- `paths.conus_zerooutside_fixed_dir`

## Quick Start

```bash
cp config/paths.example.json config/paths.json
python3 scripts/01_merge_nei_into_cams.py --config config/paths.json
python3 scripts/02_fix_time_coords.py --config config/paths.json
python3 scripts/03_combine_hourly_species_yearly.py --config config/paths.json
python3 scripts/04_regrid_to_ne0conusne30x8.py --config config/paths.json
python3 scripts/ops_singularity/zero_outside_conus_mask_c20260325.py --config config/paths.json
bash scripts/ops_singularity/fix_header_to_cams_style.sh config/paths.json
```

## Legacy/Provenance

- Unmodified original scripts are preserved under [`originals/`](originals/README.md)
  (these still contain hardcoded paths and are kept only as a historical record).
- Legacy crowded diagnostics notebook (archived):
  `originals/legacy_notebooks/Check_CAMSvsNEI_Emissions.ipynb`

## Acknowledgements

- **Gabriele (Gabi) Pfister (NCAR/ACOM)** — for guidance and assistance with the
  **NEI2022v2** anthropogenic emissions processing (the `epa_anthro_emis` preprocessing to
  hourly CONUS 0.1° files that feeds Step 1 of this workflow).
- **Duseong Jo (NCAR/ACOM)** — for the **ESMF conservative regridding** utilities
  (`Regridding_ESMF`) used at the regrid-to-`ne0CONUSne30x8` step (see *External
  dependencies* above).
- **CAMS-GLOB-ANT v6.2** anthropogenic emissions (ECMWF/CAMS).
- **NEI2022v2** — US EPA National Emissions Inventory.
- Workflow assembled by **M. Tao** for MUSICAv0 / CAM-chem regional simulations.

## License

See [`LICENSE`](LICENSE).
