from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from .config import load_json_config, require_keys


@dataclass(frozen=True)
class Settings:
    raw: Dict[str, Any]

    @property
    def workflow(self) -> Dict[str, Any]:
        return self.raw["workflow"]

    @property
    def paths(self) -> Dict[str, Any]:
        return self.raw["paths"]

    @property
    def merge(self) -> Dict[str, Any]:
        return self.raw.get("merge", {})

    @property
    def combine(self) -> Dict[str, Any]:
        return self.raw.get("combine", {})

    @property
    def regrid(self) -> Dict[str, Any]:
        return self.raw.get("regrid", {})


def load_settings(path: str | Path) -> Settings:
    cfg = load_json_config(path)
    require_keys(cfg, ["workflow", "paths"], "root config")

    workflow = cfg["workflow"]
    require_keys(
        workflow,
        [
            "start_datetime",
            "end_datetime",
            "nei_actual_year",
            "output_year",
            "date_tag",
            "inventory_name",
            "merge_token",
            "merged_label",
            "cams_label",
            "target_grid_label",
        ],
        "workflow",
    )

    paths = cfg["paths"]
    require_keys(
        paths,
        [
            "nei_hourly_dir",
            "cams_orig_dir",
            "merged_hourly_dir",
            "merged_hourly_needs_timefix_dir",
            "merged_by_species_dir",
            "map_npz",
            "regridded_output_dir",
            "cams_grid_file",
            "serr_scrip_file",
            "regridding_weights_file",
            "ncar_packages_dir",
        ],
        "paths",
    )

    return Settings(raw=cfg)
