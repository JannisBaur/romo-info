from __future__ import annotations

from pathlib import Path

import pytest

from romo_bot.config import ConfigError, Settings


def test_from_env_uses_defaults_for_optional_values() -> None:
    settings = Settings.from_env({"WHATSAPP_GROUP_JID": "123@g.us"})
    assert settings.whatsapp_group_jid == "123@g.us"
    assert settings.session_db_path == Path("data/session.db")
    assert settings.latitude == pytest.approx(55.13)
    assert settings.timezone == "Europe/Copenhagen"
    assert settings.days_to_report == 1


def test_from_env_missing_group_jid_raises() -> None:
    with pytest.raises(ConfigError):
        Settings.from_env({})


def test_from_env_respects_overrides() -> None:
    settings = Settings.from_env(
        {
            "WHATSAPP_GROUP_JID": "123@g.us",
            "SESSION_DB_PATH": "custom/session.db",
            "LATITUDE": "1.5",
            "LONGITUDE": "2.5",
            "REPORT_TIMEZONE": "UTC",
            "DAYS_TO_REPORT": "2",
        }
    )
    assert settings.session_db_path == Path("custom/session.db")
    assert settings.latitude == 1.5
    assert settings.longitude == 2.5
    assert settings.timezone == "UTC"
    assert settings.days_to_report == 2


def test_from_env_invalid_latitude_raises_config_error() -> None:
    with pytest.raises(ConfigError):
        Settings.from_env({"WHATSAPP_GROUP_JID": "123@g.us", "LATITUDE": "not-a-number"})


def test_from_env_days_to_report_below_one_raises_config_error() -> None:
    with pytest.raises(ConfigError, match="at least 1"):
        Settings.from_env({"WHATSAPP_GROUP_JID": "123@g.us", "DAYS_TO_REPORT": "0"})


def test_from_env_non_integer_days_to_report_raises_config_error() -> None:
    with pytest.raises(ConfigError):
        Settings.from_env({"WHATSAPP_GROUP_JID": "123@g.us", "DAYS_TO_REPORT": "not-a-number"})
