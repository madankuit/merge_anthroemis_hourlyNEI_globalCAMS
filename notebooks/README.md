# notebooks/

Interactive diagnostics and QA for the NEI2022v2 + CAMS v6.2 workflow. Config-driven
(no hardcoded paths); meant for exploration and figure-making, not batch production.

| Notebook | Purpose |
|----------|---------|
| `NEI2022v2_CAMSv6.2.ipynb` | Clean QA checks for the merged/mapped NEI2022v2 + CAMS v6.2 outputs: species coverage, CONUS-vs-CAMS difference maps and statistics, sanity plots. A condensed, scriptable version of these checks lives at `scripts/ops_singularity/check_cams_vs_nei_emissions.py`. |

The older, crowded diagnostics notebook is archived for provenance under
[`../originals/legacy_notebooks/`](../originals/README.md).
