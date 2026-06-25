# originals/

**Unmodified original scripts**, kept verbatim for provenance and reproducibility.
The cleaned, config-driven, run-ready versions live in [`../scripts/`](../scripts/README.md)
and [`../src/`](../src/README.md) — use those to actually run the workflow.

> ⚠️ These files intentionally still contain the author's original **hardcoded absolute
> Svante paths** and `sys.path` insertions. They are preserved as a historical record of
> exactly how the NEI2022v2 + CAMS v6.2 emissions were produced; they are **not** meant to
> be run as-is on another system.

| Original file | Cleaned equivalent |
|---------------|--------------------|
| `ModifiedFor2023_Merge_conusNEI2022v2_01degCAMS6.2_v2.py` | `scripts/01_merge_nei_into_cams.py` |
| `correct_timecoord_globCAMS_conusNEI2022_hourly.py` | `scripts/02_fix_time_coords.py` |
| `combine_hourly_globCAMS_conusNEI2022_to_species_01deg_c20260307.py` | `scripts/03_combine_hourly_species_yearly.py` |
| `Regrid_Emissions_ne0CONUSne30x8.py` | `scripts/04_regrid_to_ne0conusne30x8.py` |
| `NEIfileDatetime_shift_BYweekofday.py` | `src/nei_merge/time_shift.py` |

## legacy_notebooks/
- `Check_CAMSvsNEI_Emissions.ipynb` — the original crowded QA notebook, superseded by
  `notebooks/NEI2022v2_CAMSv6.2.ipynb` and `scripts/ops_singularity/check_cams_vs_nei_emissions.py`.
