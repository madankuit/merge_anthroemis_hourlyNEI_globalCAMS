# src/

Importable Python package(s) used by the workflow scripts. Scripts add `src/` to
`sys.path` (`REPO_ROOT / "src"`) and import from here.

- [`nei_merge/`](nei_merge/README.md) — the shared helper package: config loading,
  settings schema, day-of-week time shifting, and missing-file detection.
