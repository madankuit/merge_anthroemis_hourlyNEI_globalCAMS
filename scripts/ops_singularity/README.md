# scripts/ops_singularity/

Operational post-processing and QA steps that run **after** the numbered workflow
(`scripts/01`–`04`) to finalize emission files for a MUSICA/CAM-chem run. Named
`ops_singularity` because on Svante these are run inside a Singularity/NCO container for
the header-rewrite step. All paths come from the JSON config — no hardcoded paths.

| Script | Purpose | Run |
|--------|---------|-----|
| `zero_outside_conus_mask_c20260325.py` | Set emissions to zero outside the CONUS ~80 km buffer while preserving file structure (for additive / CONUS-only experiments). | `python3 scripts/ops_singularity/zero_outside_conus_mask_c20260325.py --config config/paths.json` |
| `fix_header_to_cams_style.sh` | Normalize NetCDF format to CAMS style for run compatibility: dimension order, variable naming, time encoding, CDF5 format (uses NCO). Reads in/out dirs from the config. | `bash scripts/ops_singularity/fix_header_to_cams_style.sh config/paths.json` |
| `check_cams_vs_nei_emissions.py` | Condensed QA: (1) species intersection between mapped outputs and CAMS references; (2) monthly-mean difference stats for one species inside the CONUS mask. | `python3 scripts/ops_singularity/check_cams_vs_nei_emissions.py --config config/paths.json --species NO --month 2023-07` |

For deeper, exploratory QA see [`../../notebooks/README.md`](../../notebooks/README.md).
