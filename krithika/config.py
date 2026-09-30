"""Typed application configuration loaded from YAML and environment variables."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


def _default_config_path() -> Path:
    """Locate user configuration beside the executable or at the source root."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "config.yaml"
    return Path(__file__).resolve().parents[1] / "config.yaml"


class BrainSettings(BaseModel):
    """Settings for the selected AI brain provider."""

    model_config = ConfigDict(extra="forbid")

    provider: Literal["claude", "gemini", "openai", "ollama"] = "claude"
    model: str = "claude-sonnet-5"
    api_key_env: str = "ANTHROPIC_API_KEY"


class ClassifierSettings(BaseModel):
    """Settings for intent classification."""

    model_config = ConfigDict(extra="forbid")

    api_key_env: str = "TYPESAFE_API_KEY"


class TTSSettings(BaseModel):
    """Settings for text-to-speech output."""

    model_config = ConfigDict(extra="forbid")

    provider: Literal["elevenlabs", "sapi"] = "sapi"
    api_key_env: str = "ELEVENLABS_API_KEY"
    voice_id: str = ""


class WakeWordSettings(BaseModel):
    """Settings for wake-word detection."""

    model_config = ConfigDict(extra="forbid")

    keyword: str = "krithika"
    access_key_env: str = "PORCUPINE_ACCESS_KEY"


class MemorySettings(BaseModel):
    """Settings for the persistent user memory store."""

    model_config = ConfigDict(extra="forbid")

    vault_path: str = ""


class KrithikaConfig(BaseSettings):
    """Application settings with environment-variable overrides."""

    model_config = SettingsConfigDict(
        env_prefix="KRITHIKA_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    brain: BrainSettings = Field(default_factory=BrainSettings)
    classifier: ClassifierSettings = Field(default_factory=ClassifierSettings)
    tts: TTSSettings = Field(default_factory=TTSSettings)
    wake_word: WakeWordSettings = Field(default_factory=WakeWordSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    log_level: Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Load YAML after environment values so secrets stay external and overridable."""

        configured_path = os.environ.get("KRITHIKA_CONFIG_FILE")
        yaml_path = (
            Path(configured_path).expanduser() if configured_path else _default_config_path()
        )
        yaml_settings = YamlConfigSettingsSource(settings_cls, yaml_file=yaml_path)
        return (
            init_settings,
            env_settings,
            yaml_settings,
            dotenv_settings,
            file_secret_settings,
        )
