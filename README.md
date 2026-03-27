# merge_anthroemis_hourlyNEI_globalCAMS

Process hourly NEI emissions and merge into CAMS anthropogenic emissions, then prepare run-ready files on `ne0CONUSne30x8`.

## Scope

Current documented workflow is for:

- NEI: `NEI2022v2`
- CAMS: `CAMS-GLOB-ANT v6.2`
- Target year: `2023`
- Grid: `ne0CONUSne30x8`

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

All runtime paths are in one external file:

- `config/paths.json` (copy from `config/paths.example.json`)

No hardcoded server paths are required in active repo scripts/notebook.

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

- Legacy crowded diagnostics notebook (archived):
  `originals/legacy_notebooks/Check_CAMSvsNEI_Emissions.ipynb`
