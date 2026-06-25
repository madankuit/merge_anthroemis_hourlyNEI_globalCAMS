# src/nei_merge/

Shared helper package imported by the workflow scripts in `scripts/`. Pure utilities —
no hardcoded paths; anything machine-specific is passed in from the JSON config.

| Module | Provides | Used by |
|--------|----------|---------|
| `config.py` | `load_json_config(path)` (reads the JSON, with a helpful error if `config/paths.json` is missing) and `require_keys()` validation. | all scripts (via `settings`) |
| `settings.py` | `load_settings(path)` → frozen `Settings` dataclass exposing `.workflow`, `.paths`, `.merge`, `.combine`, `.regrid`; validates required keys up front. | all scripts |
| `time_shift.py` | Weekday/weekend-preserving NEI filename date shifting between the NEI base year and the target simulation year (`NEIfileDatetime_shift_BYweekofday`, `extract_date_and_time`, and the backward mapper). | step 1 merge |
| `find_missing_files.py` | `find_missing_files_v1/v2()` — enumerate expected hourly filenames in a datetime range and report which are missing. | QA / diagnostics |

`__init__.py` marks the package; import as `from nei_merge.settings import load_settings`
after `sys.path.insert(0, str(REPO_ROOT / "src"))`.
