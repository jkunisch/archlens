"""Parse .archlens.yml configuration from a repository.

Loads the YAML config file and validates it against the ArchLensConfig
Pydantic schema. Returns a default (empty-rules) config when the file
is missing — this allows ArchLens to work on repos that haven't configured
rules yet (they'll still get blast radius and structural insights).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from shared.schemas.config_schema import ArchLensConfig


def load_config(repo_path: Path) -> ArchLensConfig:
    """Load and validate .archlens.yml from repo root.

    Args:
        repo_path: Path to the repository root.

    Returns:
        Validated ArchLensConfig. Returns defaults if file is missing.

    Raises:
        ValueError: If the YAML is malformed or fails schema validation.
    """
    config_path = repo_path / ".archlens.yml"
    if not config_path.exists():
        return ArchLensConfig()  # default config, no rules

    try:
        with open(config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {config_path}: {exc}") from exc

    if raw is None:
        return ArchLensConfig()  # empty file

    return ArchLensConfig.model_validate(raw)
