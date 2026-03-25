# merge_anthroemis_hourlyNEI_globalCAMS

Repository for documenting and running a general workflow to merge hourly CONUS NEI emissions into global CAMS anthropogenic emissions inventories.

1. Merge hourly CONUS NEI emissions into global CAMS emissions (with buffered CONUS mapping)
2. Fix hourly time coordinates from filename timestamps
3. Combine hourly merged files into yearly per-species files
4. Regrid species files to `ne0CONUSne30x8`

## Design Principle

No machine-specific paths are hardcoded in workflow scripts.
All paths are supplied through external config:

- `config/paths.example.json` (template in repo)
- `config/paths.json` (your local/private file, gitignored)

## Repository Layout

- `scripts/01_merge_nei_into_cams.py`
- `scripts/02_fix_time_coords.py`
- `scripts/03_combine_hourly_species_yearly.py`
- `scripts/04_regrid_to_ne0conusne30x8.py`
- `scripts/run_merge_slurm.sh`
- `src/nei_merge/` shared helper modules
- `src/nei_merge/settings.py` single config loader used by all scripts
- `config/paths.example.json` path + runtime settings template
- `config/species_mapping_template.dat`
- `originals/` archived source scripts used to build this repo
- `docs/PROJECT_INVENTORY.md` project/code inventory

## Quick Start

1. Create your private config file:

```bash
cp config/paths.example.json config/paths.json
```

2. Edit `config/paths.json` with your real directories/files and naming tokens (`inventory_name`, `merge_token`, `merged_label`, `cams_label`, `target_grid_label`).

3. Run stages:

```bash
python3 scripts/01_merge_nei_into_cams.py --config config/paths.json
python3 scripts/02_fix_time_coords.py --config config/paths.json
python3 scripts/03_combine_hourly_species_yearly.py --config config/paths.json
python3 scripts/04_regrid_to_ne0conusne30x8.py --config config/paths.json
```

## Notes

- `scripts/03_...` uses Dask (`dask.distributed`) for scalable multi-file processing.
- `scripts/04_...` requires the NCAR `dsj` package path in config (`ncar_packages_dir`).
- Species subsets can be set in config under `merge.species_subset`, `combine.species_subset`, and `regrid.species_subset`.
