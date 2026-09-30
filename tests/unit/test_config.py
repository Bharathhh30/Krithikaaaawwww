"""Unit tests for YAML and environment-backed settings."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from krithika.config import KrithikaConfig


def test_defaults_are_available_without_a_config_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A first launch without local configuration should use safe defaults."""

    monkeypatch.setenv("KRITHIKA_CONFIG_FILE", str(tmp_path / "missing.yaml"))

    config = KrithikaConfig()

    assert config.brain.provider == "claude"
    assert config.tts.provider == "sapi"
    assert config.log_level == "INFO"


def test_yaml_settings_are_overridden_by_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Environment variables take precedence over values in the YAML file."""

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "brain:\n  provider: claude\n  model: test-model\nlog_level: DEBUG\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("KRITHIKA_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("KRITHIKA_BRAIN__PROVIDER", "ollama")

    config = KrithikaConfig()

    assert config.brain.provider == "ollama"
    assert config.brain.model == "test-model"
    assert config.log_level == "DEBUG"


def test_frozen_app_loads_config_beside_executable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A packaged Windows executable reads user config from its install folder."""

    config_path = tmp_path / "config.yaml"
    config_path.write_text("log_level: DEBUG\n", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "krithika.exe"))

    config = KrithikaConfig()

    assert config.log_level == "DEBUG"


def test_invalid_yaml_value_fails_validation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Invalid configuration is reported during startup, not later in execution."""

    config_path = tmp_path / "config.yaml"
    config_path.write_text("brain:\n  provider: unknown\n", encoding="utf-8")
    monkeypatch.setenv("KRITHIKA_CONFIG_FILE", str(config_path))

    with pytest.raises(ValidationError):
        KrithikaConfig()
