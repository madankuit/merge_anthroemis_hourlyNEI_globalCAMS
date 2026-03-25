# Project Inventory (Read-through Summary)

## Source Workspace Reviewed

- `Svante_script_backup/CESM_analysis/ne0CONUSne30x8_Y2023T2024/UsingNEI2022v2/`

## Key Scripts Identified

1. `ModifiedFor2023_Merge_conusNEI2022v2_01degCAMS6.2_v2.py`
Purpose: Merge NEI2022v2 hourly emissions into CAMS v6.2 by species, using precomputed CAMS->NEI index map and buffered-CONUS replacement.

2. `correct_timecoord_globCAMS_conusNEI2022_hourly.py`
Purpose: Correct time coordinate in hourly merged files based on filename timestamp.

3. `combine_hourly_globCAMS_conusNEI2022_to_species_01deg_c20260307.py`
Purpose: Build yearly, species-wise 0.1-degree files from hourly merged files, using monthly Zarr append and final NetCDF output.

4. `Regrid_Emissions_ne0CONUSne30x8.py`
Purpose: Regrid merged species files from 0.1-degree lat/lon to ne0CONUSne30x8 via ESMF/DSJ regridding utilities.

5. `NEIfileDatetime_shift_BYweekofday.py`
Purpose: Weekday/weekend-preserving datetime shifts between NEI year and target output year.

## Main Path/Portability Issues Found

- Hardcoded absolute paths in scripts (`/net/fs09/...`, `/home/...`).
- Absolute `sys.path` insertion for helper imports.
- Workflow settings embedded at top of each script.

## Refactor Performed in This Repo

- Centralized runtime paths/settings into `config/paths.json` (external, not tracked).
- Reworked scripts to use shared config loader and local helper modules.
- Preserved original scripts under `originals/` for provenance.
