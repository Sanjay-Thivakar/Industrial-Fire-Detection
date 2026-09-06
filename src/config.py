import os
import yaml
from pathlib import Path
from typing import Any, Dict


class Config:
    """Configuration loader for the Industrial Fire AI pipeline."""

    def __init__(self, config_dict: Dict[str, Any], project_root: Path):
        self._raw = config_dict
        self.project_root = project_root

        # Resolve paths relative to project root
        paths = config_dict.get("paths", {})
        self.raw_dir = project_root / paths.get("raw_dir", "data/raw")
        self.cache_dir = project_root / paths.get("cache_dir", "data/cache")
        self.output_dir = project_root / paths.get("output_dir", "outputs")
        
        firms_zip = paths.get("firms_zip")
        self.firms_zip = Path(firms_zip) if firms_zip else None

        # Ensure directories exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Config sections
        self.project = config_dict.get("project", {})
        self.region = config_dict.get("region", {})
        self.firms = config_dict.get("firms", {})
        self.osm = config_dict.get("osm", {})
        self.spatial = config_dict.get("spatial", {})
        self.landcover = config_dict.get("landcover", {})
        self.weak_labeling = config_dict.get("weak_labeling", {})
        self.model = config_dict.get("model", {})
        self.outputs = config_dict.get("outputs", {})
        self.sentinel2 = config_dict.get("sentinel2", {})

    @classmethod
    def load(cls, config_path: str = None) -> "Config":
        """Load configuration from YAML file."""
        if config_path is None:
            # Default to config/default_config.yaml relative to workspace root
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent
            config_path = project_root / "config" / "default_config.yaml"
        else:
            config_path = Path(config_path).resolve()
            project_root = config_path.parent.parent

        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        return cls(config_dict, project_root)
