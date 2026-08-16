from __future__ import annotations

from pathlib import Path

import pytest

from romo_bot.config import ConfigError, Settings


def test_from_env_uses_defaults_for_optional_values() -> None:
    settings = Settings.from_env({})
    assert settings.output_path == Path("public/index.html")
    assert settings.latitude == pytest.approx(55.13)
    assert settings.timezone == "Europe/Copenhagen"
    assert settings.days_to_report == 1


def test_from_env_respects_overrides() -> None:
    settings = Settings.from_env(
        {
            "OUTPUT_PATH": "custom/report.html",
            "LATITUDE": "1.5",
            "LONGITUDE": "2.5",
            "REPORT_TIMEZONE": "UTC",
            "DAYS_TO_REPORT": "2",
        }
    )
    assert settings.output_path == Path("custom/report.html")
    assert settings.latitude == 1.5
    assert settings.longitude == 2.5
    assert settings.timezone == "UTC"
    assert settings.days_to_report == 2


def test_from_env_invalid_latitude_raises_config_error() -> None:
    with pytest.raises(ConfigError):
        Settings.from_env({"LATITUDE": "not-a-number"})


def test_from_env_days_to_report_below_one_raises_config_error() -> None:
    with pytest.raises(ConfigError, match="at least 1"):
        Settings.from_env({"DAYS_TO_REPORT": "0"})


def test_from_env_non_integer_days_to_report_raises_config_error() -> None:
    with pytest.raises(ConfigError):
        Settings.from_env({"DAYS_TO_REPORT": "not-a-number"})
