"""Configuration management for prx CLI via pydantic-settings + TOML."""

from __future__ import annotations

import sys
from pathlib import Path

import platformdirs
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def _user_config_path() -> Path:
    return Path(platformdirs.user_config_dir("prx")) / "config.toml"


def _project_config_path() -> Path:
    return Path.cwd() / "prx.toml"


class PrxSettings(BaseSettings):
    """Settings for prx format toolkit and hub CLI.

    Precedence (highest to lowest):
    1. Explicit constructor args
    2. Environment variables (PRX_ prefix)
    3. Project-local prx.toml
    4. User config ~/.config/prx/config.toml
    5. Defaults
    """

    model_config = SettingsConfigDict(
        env_prefix="PRX_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # prxhub
    prxhub_url: str = ""
    default_visibility: str = "public"

    # Signing
    key_path: str = ""
    auto_sign: bool = True
    identity: str = ""

    @classmethod
    def load(cls) -> PrxSettings:
        """Load settings from all sources with proper precedence."""
        config_data: dict = {}

        # Load user config (lowest precedence)
        user_path = _user_config_path()
        if user_path.exists():
            with open(user_path, "rb") as f:
                raw = tomllib.load(f)
                config_data.update(_flatten_toml(raw))

        # Load project config (overrides user config)
        project_path = _project_config_path()
        if project_path.exists():
            with open(project_path, "rb") as f:
                raw = tomllib.load(f)
                config_data.update(_flatten_toml(raw))

        return cls(**config_data)


def _flatten_toml(data: dict, prefix: str = "") -> dict:
    """Flatten nested TOML sections into dot-free keys matching settings fields."""
    result: dict = {}
    key_map = {
        "prxhub.url": "prxhub_url",
        "prxhub.default_visibility": "default_visibility",
        "defaults.visibility": "default_visibility",
        "signing.key_path": "key_path",
        "signing.auto_sign": "auto_sign",
        "signing.identity": "identity",
    }

    for section_key, value in data.items():
        if isinstance(value, dict):
            for inner_key, inner_value in value.items():
                full_key = f"{section_key}.{inner_key}"
                if full_key in key_map:
                    result[key_map[full_key]] = inner_value
        elif prefix == "" and section_key in PrxSettings.model_fields:
            result[section_key] = value

    return result
