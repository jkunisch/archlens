"""Tests for config_parser.py."""

import pytest
from pathlib import Path
from action.config_parser import load_config
from shared.schemas.config_schema import ArchLensConfig


def test_missing_file_returns_defaults(tmp_path: Path) -> None:
    """Missing .archlens.yml should return default config."""
    config = load_config(tmp_path)
    assert isinstance(config, ArchLensConfig)
    assert config.version == 1
    assert config.forbid == []
    assert config.warn == []
    assert config.thresholds.god_node_warn == 15


def test_empty_file_returns_defaults(tmp_path: Path) -> None:
    """Empty .archlens.yml should return default config."""
    (tmp_path / ".archlens.yml").write_text("")
    config = load_config(tmp_path)
    assert config.forbid == []


def test_valid_config(tmp_path: Path) -> None:
    """Valid .archlens.yml should be parsed correctly."""
    (tmp_path / ".archlens.yml").write_text("""
version: 1
forbid:
  - from: "frontend/*"
    to: "database/*"
    message: "Frontend must not access database directly"
warn:
  - from: "api/*"
    to: "internal/*"
    message: "API should not use internal modules"
thresholds:
  god_node_warn: 10
  god_node_fail: 25
ignore:
  - "vendor/*"
  - "*.generated.*"
""")
    config = load_config(tmp_path)
    assert len(config.forbid) == 1
    assert config.forbid[0].from_glob == "frontend/*"
    assert config.forbid[0].to_glob == "database/*"
    assert len(config.warn) == 1
    assert config.thresholds.god_node_warn == 10
    assert config.thresholds.god_node_fail == 25
    assert len(config.ignore) == 2


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    """Malformed YAML should raise ValueError."""
    (tmp_path / ".archlens.yml").write_text("{ invalid: yaml: [")
    with pytest.raises(ValueError, match="Invalid YAML"):
        load_config(tmp_path)
