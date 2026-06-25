# config/

All machine-specific settings live here so the scripts themselves stay path-free.

| File | Tracked? | Purpose |
|------|----------|---------|
| `paths.example.json` | yes | **Template for new users.** Placeholder paths (`<DATA_ROOT>`, `<GRID_FILES>`, `<NCAR_PACKAGES>`). Copy it to `paths.json` and edit for your own system. |
| `paths.json` | **no** (gitignored) | The config the scripts actually read (`--config config/paths.json`). Local to each machine. |
| `paths.svante.json` | yes | The **author's real Svante paths**, kept in the repo so they stay in sync between the local Mac clone and the Svante clone. On Svante: `cp config/paths.svante.json config/paths.json`. External users should ignore this and use `paths.example.json` instead. |
| `species_mapping_template.dat` | yes | Emission-inventory → CAM-chem species mapping (yields, sectors, vertical distribution, molecular weights) for the NEI2022v2 + CAMS v6.2 / TS1 mechanism. Used by the species-mapping step. Edit the `Source_fileformat` / `Destination_fileformat` paths at the top. |

## Config schema (`paths.json`)
- `workflow` — run identity: `start_datetime`, `end_datetime`, `nei_actual_year`,
  `output_year`, `date_tag`, plus labels (`inventory_name`, `merge_token`,
  `merged_label`, `cams_label`, `target_grid_label`).
- `paths` — every input/output directory and grid/mask/weight file. See
  `paths.example.json` for the full key list and what each one points to.
- `combine` / `merge` / `regrid` / `ops` — per-step tuning (Dask workers, chunking,
  distance cutoff, species subsets, etc.).

Required keys are validated on load by `src/nei_merge/settings.py`; a missing key
fails fast with a clear message.

> **Setup:** `cp config/paths.example.json config/paths.json`, then edit `paths.json`.
